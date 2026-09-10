# Consolidación final — Matrix RH 1.2.1

> Creado por Aldo Garcia. Fecha: 2026-09-10.
> Entrega de código integrada; la aceptación del servidor empresarial requiere
> sus servicios, certificados, modelos y pruebas reales.

## 1. Qué versiones se compararon

| Referencia | Identificación | Papel en esta entrega |
|---|---|---|
| GitHub original | Matrix RH 1.1.0, `94fa083b59553df18040150b4b714ae25afa5cbc` | Base funcional, estructura, convenciones y documentación histórica |
| Revisión preparada | Matrix RH 1.2.0, `472607fb268ae2277f7d4de1be012998f6cc5663` | Correcciones de autorización, modelos, persistencia, concurrencia e instalación |
| Consolidación | Matrix RH 1.2.1 | Integra ambas, corrige regresiones e integridad RAG, sincroniza documentación y empaqueta el proyecto ejecutable |

La revisión 1.2.0 era local; su existencia no prueba que GitHub o un servidor
empresarial la estuvieran ejecutando. La publicación remota, el commit final,
las pruebas ejecutadas y los límites están en
[el informe de validación](../reports/FINAL_CONSOLIDATION_VALIDATION.md).
El inventario comparativo por archivo está en
[FINAL_SOURCE_COMPARISON.md](../reports/FINAL_SOURCE_COMPARISON.md).

## 2. Lógica y estructura que se conservan

- Backend FastAPI/Python, frontend React/TypeScript y MySQL/MariaDB para estado.
- Qdrant para documentos corporativos y adjuntos privados en colecciones separadas.
- Orquestador, agente de conocimiento y herramientas RAG/SQL en sus directorios.
- Identidad literal `Soy Matrix RH.`, historial, fuentes, cargas y publicación
  administrativa dentro de categorías autorizadas.
- Perfiles HCM acumulativos, rol base, segregación de datos sensibles y control
  de permisos en la recuperación; ningún modelo amplía permisos.
- Proveedor `local_test` para desarrollo/pruebas y proveedor Entra preparado
  para activación por TI, sin fallback automático entre proveedores.
- Corpus `data/knowledge/general` y `data/knowledge/especializadas`, scripts
  Windows existentes, migraciones previas y convenciones de nombres.
- Documentación y auditorías históricas. Sus fechas y resultados originales no
  se convierten en evidencia de pruebas de esta versión.

Los nombres heredados `OLLAMA_FAST_MODEL`, `OLLAMA_DEEP_MODEL` y
`get_ollama_client()` permanecen por compatibilidad. La fachada resuelve el
protocolo sin cambiar el contrato de negocio.

## 3. Matriz de decisiones

| Componente | GitHub 1.1.0 | Revisión 1.2.0 | Decisión final 1.2.1 |
|---|---|---|---|
| Identidad y autenticación | Local de pruebas + Entra OIDC | Añade OIDC interno y correlación del navegador | Conservar rutas y flags; endpoint accesible no se declara login real validado |
| Autorización e historial | Categorías en turnos; cobertura incompleta en resúmenes/historial | Huella de alcance y revalidación antes de publicación | Conservar protección; identidad exacta sigue visible sin eximir otros contenidos de ACL |
| Modelos | Protocolo Ollama ligado al cliente | Interface para Ollama/API compatible/Vertex; `.env` único | Conservar adapters y validar formatos reales; cloud desactivado en perfil local |
| Salida estructurada | Plan validado antes de compilar SQL | Schema común y normalización por proveedor | Precisar tipos del schema de filtros sin permitir SQL libre |
| Datos e inferencia | Sesión SQL durante trabajo lento | Transacciones cortas, operaciones identificables, cupos/deadline | Conservar; no presentar los límites por proceso como cola distribuida |
| Actualización del índice | Borrado previo a nueva escritura | Generaciones activadas mediante manifest SQL | Conservar activación; pipeline 5/extractor 3 invalida extracción anterior |
| Adjuntos de un servidor anterior | Ruta persistida y colección privada | Huella nueva requiere reconstrucción | Reconciliar privados desde root restaurado, verificar SHA y conservar ID/owner/conversación |
| Extracción DOCX | Tablas procesadas después de todos los párrafos | Mismo defecto conservado | Corregir orden real para mantener tabla y sección asociadas |
| Contexto documental | Corte fijo por caracteres de cada fragmento | Mismo riesgo de perder excepciones | Empaquetar evidencias completas; comunicar omisiones por presupuesto |
| Grounding | Cita válida aceptada como respaldo | Coincidencia textual parcial y cifras | Exigir unidades completas; separar fidelidad extractiva de veracidad factual |
| Recuperación | Dense + dedup + MMR; diversidad posterior al corte | Diversidad antes del corte; índices de payload servidor | Conservar Qdrant y esa mejora; no declarar BM25 ni cross-encoder inexistentes |
| Frontend | Estado global susceptible a respuestas tardías | Asociación de operaciones y cargas a conversación | Consolidar con el contrato API y entregar build; validación detallada en informe final |
| Instalación | Scripts Windows y Docker existentes | `install.bat`, prerrequisitos y rutas portables | Conservar entradas; comprobar propiedad de BD y actualizar guías y locks |
| Documentación | Guías y reportes 1.1.0 | Añade AD, proveedores, fine-tuning y despliegue v2 | Mantener históricos, corregir instrucciones contradictorias y enlazar evidencia nueva |

Las entradas de changelog con bug → causa → corrección están en
[README.md](../README.md) y [CHANGELOG.md](../CHANGELOG.md). La comparación
no es una migración estética de carpetas ni una sustitución del producto original.

## 4. Ejecución en un servidor Windows nuevo

1. Aprovisionar manualmente Python 3.12 x64, uv 0.12.8, Node 22.12+ y Corepack,
   MySQL/MariaDB y runtime/modelos configurados. WAMP puede proporcionar MySQL;
   PHP no ejecuta este backend. Para Qdrant servidor, aprovisionarlo internamente.
2. Extraer el proyecto completo en una carpeta estable. Conservar `.env.example`
   como referencia y preparar `.env` con credenciales propias, rutas válidas y
   endpoints internos. No copiar ejecutables `.venv` de otro servidor.
3. Iniciar MySQL y el runtime; ejecutar **`install.bat`**. Este delega en el flujo
   existente de instalación y arranque, instala dependencias, inicializa o migra
   la BD propia, prepara la interfaz y comprueba las dependencias.
4. Confirmar `/health`, `/ready`, login, conversación, pregunta documental con
   fuente y carga privada. Un `/health` positivo sólo acredita proceso vivo.
5. Para arranques posteriores usar `INICIAR_MATRIX_RH.bat`; para detener o
   diagnosticar usar los `.bat` correspondientes que ya existían en el proyecto.

El ZIP incluye frontend compilado. `-SkipFrontend` sólo es válido al conservar
ese build; no debe usarse para ocultar fallos de instalación. Un destino sin
Internet necesita caches de dependencias para Windows y pesos preparados;
`-Offline` no descarga ni inventa lo que falta. El script no instala drivers,
servicios privilegiados, certificados, AD ni modelos de decenas de GB.

Checklist operativo, opciones, actualización de datos, rollback y prueba de
carga: [DEPLOYMENT_V2.md](DEPLOYMENT_V2.md).
Alternativa Docker y configuración propia de contenedores:
[DEPLOYMENT.md](DEPLOYMENT.md).

## 5. Actualización y trazabilidad

Antes de actualizar una instalación existente, detener Matrix y respaldar
conjuntamente `.env`, MySQL, corpus, adjuntos y Qdrant. Aplicar las migraciones
incrementales 0004–0006 sin alterar las anteriores y reingerir el corpus con
pipeline 5/extractor 3. La reconstrucción es necesaria aunque los archivos DOCX
no hayan cambiado de SHA: su extracción anterior podía asociar tablas a una
sección equivocada.

Copiar también `var/uploads` completo. La reconciliación migra adjuntos privados
desde el root configurado y comprueba el SHA original, conservando su ID, dueño
y conversación. Los fallos por archivos faltantes o alterados quedan en el job;
una ruta absoluta antigua no concede acceso fuera del root privado restaurado.

Los turnos/resúmenes históricos sin alcance verificable permanecen en SQL,
ocultos conservadoramente; no se les asignan automáticamente permisos actuales.
Los documentos de huella anterior no se reutilizan como si ya estuvieran
reindexados. Cambiar dimensión de embeddings requiere nuevas colecciones.
Para volver atrás, restaurar un conjunto coherente de código, BD y vector store.

El paquete conserva un `source-history.bundle` para consultar la historia Git
sin depender de acceso remoto. Es opcional para ejecutar Matrix. Con Git instalado,
desde la carpeta donde esté el bundle:

```bash
git clone source-history.bundle MatrixRH-source
git -C MatrixRH-source log --oneline -5
git -C MatrixRH-source diff 94fa083 472607f -- docs backend frontend windows
git -C MatrixRH-source diff 472607f HEAD -- docs backend frontend windows
```

El inventario final registra archivos conservados, modificados y añadidos. La
historia permite revisar por qué cambió cada componente sin borrar su contexto.

## 6. AD y operación completamente local

`AUTH_PROVIDER=local_test` mantiene las pruebas actuales sin activar Entra ni
pedir sus credenciales. Producción exige desactivar usuarios/flags sintéticos y
usar SSO. Para operación local: `AUTH_PROVIDER=oidc` con IdP interno federado a
AD; para Entra: `AUTH_PROVIDER=entra`, que implica dependencia cloud. LDAP/LDAPS
pertenece a la federación del IdP, no a un bind directo inexistente en Matrix.

Se conserva toda la documentación de Entra y el
[checklist TI de AD](integrations/AD_ACTIVATION_CHECKLIST.md).
`LLM_LOCAL_ONLY=true` bloquea Vertex; cambiar el generador o un runtime compatible
requiere editar `.env`, instalar los pesos elegidos y ejecutar las regresiones.
El adapter no demuestra que dos modelos tengan la misma calidad.

## 7. Alcance real y trabajo que sigue sujeto a aceptación

- La fidelidad extractiva evita aceptar una frase parcial que invierte una
  negación; no demuestra vigencia, corrección o suficiencia del documento fuente.
  `factual_verified` no certifica una exactitud del 100 % y la ruta general sin
  evidencia documental no se etiqueta como `grounded`.
  Tras dos rechazos, la consulta documental conserva la respuesta de
  insuficiencia de GitHub; el fallback extractivo se reserva al resumen.
  La validación estricta puede aumentar abstenciones ante paráfrasis correctas;
  no demuestra una mejora semántica sin evaluación real.
- No se incorporan automáticamente OCR, PowerPoint, búsqueda híbrida BM25,
  glosario corporativo, multi-query ni reranker entrenado. Son extensiones
  propuestas que requieren corpus y evaluación; no sustituyen las correcciones.
- No se realiza fine-tuning. La decisión fundamentada y comparación de frameworks
  están en [LOCAL_FINETUNING.md](LOCAL_FINETUNING.md).
- No se certifican 200 usuarios sostenidos/250 en pico mediante pruebas unitarias.
  Qdrant embedded, cupos por proceso y ausencia de cola distribuida son límites
  explícitos. Medir calidad, errores, latencia y recuperación en hardware real.
- Las pruebas Windows, Docker, SSO, motores SQL externos y modelos reales sólo
  se consideran ejecutadas si así lo identifica el informe de validación. Un
  workflow preparado o un transporte HTTP simulado no equivalen a esa ejecución.

## 8. Orden de lectura

1. [README.md](../README.md): requisitos, arranque y changelog de esta entrega.
2. [OPERATOR_QUICKSTART.md](OPERATOR_QUICKSTART.md): operación cotidiana.
3. [ARCHITECTURE.md](ARCHITECTURE.md), [AI_DESIGN.md](AI_DESIGN.md) y
   [RAG_DESIGN.md](RAG_DESIGN.md): flujo conservado y contratos vigentes.
4. [MODEL_PROVIDERS.md](MODEL_PROVIDERS.md),
   [DATA_MODEL.md](DATA_MODEL.md) y
   [AD_ACTIVATION_CHECKLIST.md](integrations/AD_ACTIVATION_CHECKLIST.md):
   configuración, migraciones y activación TI.
5. [FINAL_CONSOLIDATION_VALIDATION.md](../reports/FINAL_CONSOLIDATION_VALIDATION.md):
   evidencia ejecutada y límites de la entrega.
