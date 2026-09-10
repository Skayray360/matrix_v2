# Auditoría de arquitectura, E2E y modelos locales

> Creado por Aldo Garcia. 2026-09-10.
> Base inspeccionada: v1.2.1, commit `6ba83f31df93a78cd562dce5be2bcdccd2193681`.
> Correcciones acotadas entregadas en v1.2.2. GitHub `main` no se modifica.

## Dictamen

La estructura modular permite continuar con el proyecto sin sustituir su stack.
No hay evidencia para afirmar que los modelos locales estén aprovechados al
máximo ni que soporte 200–250 consultas. El principal freno de calidad es el
contrato extractivo de respuesta, seguido por la selección/fragmentación de
evidencia y la falta de mediciones reales. No aprobar capacidad ni exactitud
factual basándose en la cantidad de pruebas unitarias aprobadas.

Se conservan carpetas, documentación histórica, autorización, AD/Entra inactivo,
identidad fija, interfaz y rutas. No se implementa un nuevo pipeline semántico
como parte de una auditoría ni se afirma que los hallazgos abiertos estén resueltos.

## Arquitectura y estructura

| Capa real | Evaluación | Decisión |
|---|---|---|
| FastAPI + React same-origin | Sesión/CSRF/ACL en backend; UI no concede permisos | Conservar |
| Orquestador, RAG, agente, adapter | Responsabilidades separadas; conocimiento recibe evidencia autorizada | Conservar límites y corregir contratos concretos |
| MySQL | Estado, permisos, historial y activación de generaciones; se libera SQL antes de inferencia | Conservar, medir pool bajo carga real |
| Qdrant embebido | Adecuado para instalación de un proceso; bloquea acceso concurrente de otros procesos al mismo directorio | Perfil de capacidad: Qdrant servidor interno |
| Admisión en memoria | Evita trabajo ilimitado; 4 chats y 2 inferencias por proceso; no hay cola compartida | Cola local acotada antes de escalar API |
| Ollama | Modelos configurables, esquema validado, sin reintentos por saturación | Elegir modelo/perfil con calidad y rendimiento medidos |
| Verificador extractivo | Preserva unidades, cifras y condiciones; no prueba pertinencia ni comprensión | Rediseño evaluado antes de habilitar paráfrasis |
| E2E y evaluación | Playwright real definido; mayoría de evidencia disponible usa dobles | Validar con servicios y corpus de prueba aislados |

## Hallazgos confirmados y estado

Todas las correcciones y propuestas siguientes permiten operación completamente
local. Las reproducciones usan código real y datos/transportes sintéticos; no
son resultados del servidor empresarial ni respuestas medidas de Gemma/Qwen.

| ID | Severidad | Evidencia en la base v1.2.1 | Impacto | Fix concreto / estado |
|---|---|---|---|---|
| A01 | Alta | `model_policy.py`, atajo de saludo anterior a documental | «Hola, ¿cuántos días de vacaciones…?» evitaba RAG | **Corregido:** saludo conserva intención documental; 14 regresiones |
| A02 | Alta | `knowledge_agent.py` presupuestaba antes de insertar `LLM_SYSTEM_PREFIX` | Se enviaban 30687 caracteres frente a presupuesto calculado de 18072 | **Corregido en KnowledgeAgent:** reservar prefijo y overhead; planner separado sigue pendiente |
| A03 | Alta | `orchestrator.py::_gather_tools`, resumen privado primero incondicional | Resumen corporativo devolvía menú adjunto | **Corregido:** resolver ámbito explícito corporativo/privado/mixto, conservar flujo genérico |
| A04 | Media | `retriever.py::deduplicate`, texto como única identidad | Comparación perdía una empresa si su política coincidía con otra | **Corregido en comparativas:** preservar documento/categoría de cada fuente |
| A05 | Alta | `test_reconciler.py` borra documentos corporativos y confirma; validador usa BD configurada | Ejecutar pruebas podía alterar datos operativos | **Corregido:** guard de entorno/BD/rutas desechables antes de fixtures y validación Windows |
| A06 | Alta | `tests/e2e/helpers.ts::ask`, última respuesta sin correlación | Una respuesta anterior podía validar un envío fallido | **Corregido:** correlación POST, HTTP, conversación y message_id nuevos |
| A07 | Media | `load_test.py` contaba HTTP antes de validar y volvía a contar el error | 7 POST malformados se reportaban como 14 intentos | **Corregido:** un resultado por intento y contrato mínimo de respuesta |
| A08 | Media | `ollama_client.py` descartaba duraciones del runtime | No se distinguía carga, prompt y generación | **Añadido:** métricas numéricas en `ChatResult`/log y diagnóstico local sin inferencia |
| A09 | Alta | `grounding.py::verify_grounding` no recibe pregunta; compara unidades completas | Paráfrasis correcta rechazada; copia irrelevante aceptada | **Pendiente:** pertinencia y soporte por afirmación, evaluación local calibrada; no relajar a substring |
| A10 | Alta | `knowledge_agent.py`, cobertura de citas <0.34 sobre todo top_k | Una respuesta correcta de 25% con 1 fuente útil/6 provoca otra generación idéntica | **Pendiente:** cobertura de aspectos pedidos y evidencia pertinente, con evaluación pareada |
| A11 | Alta | `chunking.py`, bloque de tabla largo se divide por frases/palabras | Tabla de 160 filas termina en 3 chunks de una línea, sin encabezados posteriores | **Pendiente:** filas completas, encabezados, unidades y notas; reindexar después |
| A12 | Alta | `chat.py::cancel_chat` actualiza SQL; transporte y resumen no consultan cancelación en cada etapa | GPU sigue trabajando y el resultado se descarta al final | **Pendiente:** cancelación cooperativa y cierre de transporte compatible; demostrar liberación de cupos |
| A13 | Alta | `settings.py` 4 chats/2 inferencias, `admission.py` rechaza sin esperar | Ráfaga válida puede recibir 503 incluso con cupo de chat | **Pendiente:** cola compartida acotada, prioridad/cupos por tarea; dimensionar por medición |
| A14 | Media | `model_policy.py::generation_profile` identifica perfil por nombre | FAST=DEEP usa 32768/2048 aunque ruta sea fast8192/768 | **Pendiente:** separar perfil e identificador; mientras, presupuestos iguales para nombre compartido |
| A15 | Alta | `query_planner.py` no aporta num_ctx ni limita catálogo; estimación global no usa tokenizer real | Prompt/schema/prefijo pueden exceder ventana al cambiar modelo/runtime | **Pendiente:** presupuesto de catálogo/schema y tokenizer del artefacto; no cortar esquema silenciosamente |
| A16 | Media | `provider.py::embedding_revision`, `indexing_fingerprint` | Dos consultas idénticas generan 4 inventarios y 1 embedding; cambio de digest entre pasos es posible | **Pendiente:** manifiesto coherente por operación/despliegue, sin mezclar huellas |
| A17 | Alta | Golden set de 36 casos sin `expected_source_ids` | Recall/MRR/corrección de fuente no medidos | **Corregido el instrumento en esta entrega:** anotaciones verificadas sobre corpus sintético; ejecución real pendiente |
| A19 | Media | `OllamaClient.embed` no especifica `truncate`; chunking admite hasta 8000 tokens estimados | Runtime puede truncar texto de embeddings sin que la dimensión revele pérdida | **Pendiente:** rechazo explícito de exceso, presupuesto del embedding y nueva huella al cambiar política |
| A18 | Alta | `run_quality_gate.py` y validador Windows solo bloqueaban FAIL | Omitir E2E/servicios podía anunciar aprobación completa | **Corregido:** INCOMPLETE/salida 2 y comprobación JUnit de casos obligatorios |

A19 es un riesgo condicionado a entradas que excedan la ventana del embedding,
no una pérdida medida en el despliegue. Ollama documenta `truncate=true` por
defecto en `/api/embed`.
[Contrato oficial de embeddings](https://docs.ollama.com/api/embed).

## Evidencia E2E: qué existe y qué falta

Playwright recopila **28 pruebas en 4 specs**, con un worker Chromium y backend
same-origin existente. Esa serialización protege la batería funcional de modelos
locales; no constituye una prueba de concurrencia. No se ejecutó el navegador
contra la pila completa: aquí faltan MySQL, Ollama, GPU accesible y Chromium de
Playwright. `--list` demuestra recopilación, no aprobación de los escenarios.

La CI preparada ejecuta contratos, Vitest/build y una selección de integración
MySQL. No ejecuta modelos instalados ni navegador con GPU. Los transportes
controlados prueban el adapter/schema; no demuestran intercambiabilidad funcional
entre pesos reales. La validación Windows se revisa estáticamente en este Linux.

Se corrigió `04-operations.spec.ts`: modelos y parámetros proceden del diagnóstico
y cada evento se correlaciona con el X-Request-ID del chat actual. Se conserva
la expectativa de ruta rápida para la pregunta documental simple; el pipeline
real puede escalar por categorías/cobertura y esa política sigue pendiente de
calibración.

Brechas adicionales del catálogo E2E que requieren ampliar escenarios:

- Ingesta E2E completa de PDF/DOCX/XLSX; la batería actual usa MD/TXT.
- Canarios sintéticos de contenido confidencial además de buscar nombres de
  fuentes en las aserciones negativas.
- Falta el ciclo completo de revocación durante generación, saturación con
  recuperación, cambio de modelo real y migración de índice bajo consultas.
- El corpus sintético no reemplaza un conjunto aprobado por RH con políticas,
  vigencias, excepciones, lenguaje habitual y preguntas sin respuesta.

## Resultados de esta entrega

| Comprobación ejecutada | Resultado | Límite |
|---|---|---|
| Backend unitarias + seguridad + integración | **716 aprobadas, 154 omitidas, 0 fallos, 870 recopiladas** | 153 requieren MySQL; una requiere visibilidad del proceso hijo en /proc |
| Frontend Vitest | **29 aprobadas** | Incluye cinco pruebas del helper con dobles; no es navegador real |
| Typecheck y build frontend | Aprobados | Build incluido; no certifica servicios de destino |
| Playwright `--list` | **28 pruebas / 4 specs** | Recopilación, no ejecución |
| Anotaciones RAG | **22/22 grounded con fuentes y hechos**, 36 casos totales | Perfil 900/120, documentos sintéticos; ningún modelo real evaluado |
| Ruff de app/archivos modificados, encabezados y parseo shell | Aprobados | PowerShell revisado estáticamente; Windows no disponible |
| Secretos y SAST de app | Sin secretos reales ni hallazgos SAST pendientes en el análisis ejecutado | Las credenciales sintéticas de tests llevan excepciones individuales documentadas |
| Diagnóstico local | Ejecutado: Ollama inaccesible; nvidia-smi ausente | No inventa GPU/VRAM ni mide servidor empresarial |

Comandos principales ejecutados desde la raíz:

```bash
backend/.venv/bin/python -m pytest backend/tests/unit backend/tests/security backend/tests/integration --junitxml=/ruta/evidencia.xml
```

Desde `frontend`: `corepack npm run typecheck`, `corepack npm test`,
`corepack npm run build`, `corepack npm run e2e -- --list`. También se comprobó
TypeScript de los specs E2E mediante `tsc --noEmit` explícito. No se ejecutó
el quality gate completo dependiente de servicios; la aceptación permanece
**incompleta**, aunque las regresiones disponibles hayan aprobado.

La corrección adicional de orden de imports del parser aislado resuelve el
fallo Ruff observado al revisar esta base; conserva sus anotaciones SAST
específicas, el comando fijo y `shell=False`. No cambia la extracción.

## Priorización para aprovechar el hardware

Estimaciones de ingeniería, sin adquisición ni curación de todo el corpus.
El orden refleja dependencia y riesgo, no una promesa de velocidad del modelo.

| Orden | Acción | Esfuerzo | Dependencia / aceptación |
|---|---|---:|---|
| 1 | Ejecutar batería segura y establecer baseline de calidad y tiempos | 1–3 días + revisión RH | Correcciones 1.2.2 y servidor; guardar modelos/digests/config y fuentes esperadas |
| 2 | Resolver verificación de afirmaciones/pertinencia y abstención | 3–6 días | 1; paráfrasis válidas aceptadas sin perder negaciones ni admitir extractos irrelevantes |
| 3 | Reparar tablas, alinear unidades/contexto/salida y límite de embeddings | 2–4 días | 1; reindexar copia y verificar cifras/encabezados/condiciones |
| 4 | Evitar escalados sin beneficio y separar perfil de modelo | 1–3 días | 1–2; mismo conjunto en rápido/profundo, menos llamadas sin caída de calidad |
| 5 | Implementar cancelación efectiva y cola local acotada | 4–7 días | Contrato de estado/API; trabajo cancelado deja de consumir etapas posteriores |
| 6 | Qdrant servidor, runtime/VRAM y contexto/paralelismo medidos | 2–4 días | 1 y 5 para escalar; no recomendar aumentar workers con índice embebido |
| 7 | Comparar recuperación híbrida/reranker/vecinos locales | 2–5 días | 1 y 3; mejora en fuentes esperadas que compense latencia añadida |
| 8 | E2E real ampliado y carga 200/250 con recuperación | 3–5 días | 2–7, hardware y SLO; reportar también rechazos/omisiones/calidad |

No recomiendo fine-tuning en esta fase: los fallos reproducidos son de código,
contexto y medición. Entrenar no repara un verificador que rechaza paráfrasis,
una tabla fragmentada o un ámbito de fuente equivocado.

## Cómo continuar en el servidor

El procedimiento ejecutable, matriz de experimentos, variables y límites están
en [LOCAL_MODEL_OPTIMIZATION.md](../docs/LOCAL_MODEL_OPTIMIZATION.md). Primero
ejecutar `scripts.local_model_diagnostics`; luego la batería aislada descrita en
[TESTING.md](../docs/TESTING.md). No ejecutar fixtures de integración sobre la
base habitual. Una GPU de 16 GB mencionada previamente es inventario histórico;
no se presupone que siga siendo el equipo destino ni que aloje todos los modelos.

Los nombres `gemma4:latest` y `qwen3.6:latest` no prueban número de parámetros,
cuantización ni memoria requerida. Ollama permite observar residencia con
`ollama ps`; estar completamente cargado en GPU es distinto de utilizar toda
su capacidad y distinto de cumplir un SLO.
[Residencia y paralelismo de Ollama](https://docs.ollama.com/faq).
