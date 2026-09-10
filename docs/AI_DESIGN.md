# Diseño de IA — Matrix RH

> Creado por Aldo Garcia.

El perfil predeterminado de Matrix RH usa dos LLM locales con rutas
deterministas. La capacidad general se mantiene separada de la ruta de políticas,
documentos y datos internos, que requiere evidencia y ACL. Desde 1.2.0 el contrato
`InferenceClient` permite seleccionar otro runtime mediante `.env`; el adapter
Vertex está preparado y bloqueado en el perfil local. Véase
[MODEL_PROVIDERS.md](MODEL_PROVIDERS.md).

## 1. Agentes y fronteras

| Componente | Responsabilidad | Frontera |
|---|---|---|
| Orquestador | Clasificar intención, autorizar, elegir herramienta/modelo, auditar | No sintetiza desde fuentes sin pasar por su tool |
| Tool RAG | Recuperar corporativo con categorías o adjuntos con ownership | No amplía categorías ni devuelve texto fuera del filtro Qdrant |
| Tool estructurada | Ejecutar un plan validado sobre fuentes concedidas | No acepta SQL libre |
| Agente de Conocimiento | Sintetizar y verificar citas sobre evidencia recibida | No conoce el vector store ni el motor de políticas |

La autorización ocurre antes de recuperar o construir el prompt. El texto de un
documento se trata como dato no confiable, nunca como instrucción.

## 2. Intenciones y contrato de identidad

La clasificación vive en `backend/app/llm/model_policy.py`, no en un LLM. Es
normalizada, determinista y no consume inferencia.

| Intención | Detección | Ejecución |
|---|---|---|
| `identity` | «quién eres», «cómo te llamas», «identifícate», equivalentes | Respuesta exacta `Soy Matrix RH.` sin RAG ni LLM |
| `document_summary` | «resume», «resumen», «sintetiza», «puntos clave», «ideas principales» | Adjuntos privados por metadata; si no hay adjunto, RAG corporativo autorizado |
| `documental` | Referencia a documento/fuente o vocabulario de RH: política, nómina, vacaciones, salario, etc. | RAG con ACL; sin evidencia se declara insuficiencia |
| `structured` | Marcadores de conteo o agregación sobre personas/datos | Plan estructurado validado y fuente concedida |
| `mixed` | Señales documentales y estructuradas | Ambas tools; evidencia separada |
| `conversational` | Saludos/despedidas cortos | Ruta general sin fuentes internas |
| `general` | Solicitud fuera de RH y sin referencia documental | Conocimiento general del modelo, sin citas corporativas |

El orden busca mantener separadas la insuficiencia documental y la conversación
general. La revisión 1.2.0 añade vocabulario RH y continuidad para determinados
seguimientos mediante memoria autorizada. Sigue siendo un clasificador de reglas:
no reconoce necesariamente todas las siglas ni paráfrasis corporativas. La ruta
general tiene un *system policy* separado que prohíbe presentar su respuesta como
dato de la empresa; esa instrucción no es una garantía semántica.

## 3. Política de los dos modelos

### Ruta rápida — `gemma4:latest`

Es la selección predeterminada para conversación, conocimiento general,
preguntas documentales normales y resúmenes cortos. Su presupuesto busca menor
latencia sin sacrificar una respuesta sustantiva:

| Parámetro | Valor predeterminado |
|---|---:|
| `OLLAMA_FAST_NUM_CTX` | 8 192 |
| `OLLAMA_FAST_MAX_TOKENS` | 768 |

### Ruta profunda — `qwen3.6:latest`

Se usa cuando al menos una señal justifica razonamiento o contexto adicional:

| Señal auditable | Condición |
|---|---|
| `deep_marker_in_query` | comparación, análisis profundo, contradicciones, implicaciones, etc. |
| `long_query` | consulta de 320 caracteres o más |
| `multiple_questions` | más de dos signos `?` |
| `multi_category_comparison` | evidencia de dos o más categorías |
| `multi_tool_flow` | RAG y datos estructurados en el mismo turno |
| `low_retrieval_confidence` | mejor score menor que `RAG_MIN_SIMILARITY + 0.05` |
| `verifier_requested_deep` | el verificador solicita cobertura adicional |
| `mixed_intent` | intención mixta |
| `large_document_summary` | resumen con más de 4 chunks o más de 10 000 caracteres de evidencia |

| Parámetro | Valor predeterminado |
|---|---:|
| `OLLAMA_DEEP_NUM_CTX` | 32 768 |
| `OLLAMA_DEEP_MAX_TOKENS` | 2 048 |

La temperatura depende de la tarea: por defecto `LLM_GENERAL_TEMPERATURE=0.25`,
`LLM_SUMMARY_TEMPERATURE=0.08`, `LLM_TEMPERATURE=0.10` y
`LLM_RETRY_TEMPERATURE=0.03`. `LLM_TOP_P=0.9` también se configura en `.env`.
Los presupuestos son límites de inferencia, no promesas de calidad ni de tiempo.

## 4. Resumen de adjuntos

Un resumen no es una búsqueda semántica. «Resume esto» puede no compartir ninguna
palabra con el archivo, por lo que Matrix RH no genera embedding ni aplica
`RAG_MIN_SIMILARITY` en esta ruta.

1. Qdrant hace `scroll` sobre la colección privada.
2. El filtro `MUST` contiene `scope=conversation`, `owner_user_id` y
   `conversation_id`.
3. Los chunks se ordenan por archivo e índice y se deduplican.
4. Se escanean como máximo `RAG_SUMMARY_SCAN_MAX_CHUNKS=256`.
5. Si la evidencia cabe en el contexto elegido, se hace una síntesis con citas.
6. Si no cabe, se divide en lotes de hasta
   `RAG_SUMMARY_MAX_CHUNKS=24` y presupuesto de contexto: el perfil rápido procesa
   los lotes secuencialmente y el profundo integra los parciales.
7. Se validan fuentes y unidades extractivas completas; el fallback preserva
   condiciones y avisa cuando el presupuesto impide incluir toda la evidencia.

Si existen chunks legibles pero el modelo declara insuficiencia, se permite una
regeneración. Si vuelve a hacerlo o no conserva citas válidas, se entrega un
resumen extractivo citado; nunca se transforma evidencia real en un falso vacío.
Si había más de 256 chunks, la respuesta indica explícitamente que se procesó
material hasta ese límite.

Esta ruta no permite elegir un archivo concreto cuando hay varios adjuntos: el
alcance técnico es la conversación completa. Para aislar un documento, utilice
una conversación nueva.

## 5. Grounding y regeneración

| Riesgo | Control |
|---|---|
| Documento sin evidencia | no se llama al modelo; respuesta de insuficiencia |
| Fuente inventada | `verify_grounding` compara citas con fuentes documentales y SQL permitidas |
| Negación, sujeto o condición omitidos | Validación extractiva de unidades completas; no aceptación por substring |
| Cobertura pobre con evidencia rica | una regeneración; si vuelve a fallar, insuficiencia documental. El fallback extractivo completo se reserva al resumen |
| Memoria usada como hecho | bloque separado, marcado como no factual |
| Prompt injection documental | delimitadores + política + ausencia de herramientas privilegiadas |
| Fuga entre adjuntos | ownership en el filtro Qdrant, no posfiltrado |
| Resumen largo pierde secciones | map/reduce con verificación; fallback a parciales o extractivo |

Sólo hay una regeneración de calidad. Un HTTP 404 específico del modelo permite
el fallback configurado; 429/503 y errores de transporte no disparan otro modelo
sobre el mismo servicio. `LLM_LOCAL_ONLY=true` bloquea Vertex. Habilitarlo exige
una configuración explícita incompatible con el requisito de inferencia local;
el fallo de un runtime no lo activa automáticamente.

`extractive_verified` comprueba fidelidad textual y `citations_valid` la
allowlist. `factual_verified=False` expresa que no hay verificación semántica
calibrada. Estos controles no demuestran que el documento fuente sea correcto,
vigente o suficiente; una paráfrasis válida también puede ser rechazada.

## 6. Rendimiento local

- `OLLAMA_KEEP_ALIVE=15m` reduce recargas del modelo entre turnos.
- El cliente HTTP reutiliza hasta 20 conexiones, 10 en *keep-alive*, con timeout
  de conexión acotado a 10 s.
- Las consultas repetidas reutilizan un LRU de 256 embeddings, identificado por
  modelo + revisión/digest + SHA-256; la clave no guarda el texto.
- Gemma atiende la ruta normal; Qwen sólo se carga cuando una señal aporta valor.
- El resumen largo ejecuta mapas secuenciales dentro del deadline compartido.
- Los cupos iniciales son `CHAT_MAX_INFLIGHT=4` e `INFERENCE_MAX_INFLIGHT=2`
  por proceso; el exceso se rechaza. `LLM_REQUEST_DEADLINE_SECONDS=120` es el
  presupuesto compartido de las llamadas del turno, no 600 segundos por intento.
- No hay cola durable distribuida. Estos cupos protegen recursos; no acreditan
  servicio simultáneo para 200–250 usuarios.

La latencia real depende de RAM, VRAM, reparto CPU/GPU, tamaño de contexto y
estado de carga. `ollama ps` muestra dónde está ejecutándose cada modelo; los
eventos `chat.answer` conservan modelo y `latency_ms`.

## 7. Control de contexto

| Elemento | Límite predeterminado |
|---|---:|
| Mensaje del usuario | 8 000 caracteres |
| Evidencia documental por chunk | Unidad completa; no corte a 2 200 caracteres |
| Evidencia de resumen por chunk | Unidad completa; no corte a 2 600 caracteres |
| Turnos recientes | 6 configurables |
| Texto por turno reenviado | 1 200 caracteres |
| Filas estructuradas en prompt | 25 |
| Scan privado para resumen | 256 chunks |
| Lote de resumen | 24 chunks |

El presupuesto del prompt se calcula como
`max(0, num_ctx - max_tokens - 1400) * 3` caracteres y se contrasta con el prompt
serializado completo, incluidos sistema, pregunta, memoria, alcance y retry.
Las tablas SQL y unidades documentales completas tienen prioridad sobre la
memoria conversacional cuando compiten por ese presupuesto. El fallback a un
perfil menor repite la comprobación. La
omisión de evidencia por falta de espacio se comunica. No es el tokenizador real
ni sustituye una medición de cada modelo/runtime.

El resumen interno de una conversación es sólo continuidad de diálogo. Además
del prompt que prohíbe cifras y políticas, su uso depende de una huella del
alcance autorizado vigente. Mensajes y resúmenes sin procedencia verificable se
ocultan conservadoramente; los permisos se revalidan antes de publicar la respuesta.

## 8. Evaluación y límites

Los controles de routing, identidad, separación general/documental, ACL privada,
resumen, fallback y parámetros tienen pruebas unitarias. El RAG corporativo usa
un golden set sintético y el gate crítico sigue siendo **0 % de fuga ACL**.

Límites deliberados:

- no hay streaming: las citas se verifican antes de mostrar la respuesta;
- un PDF sin texto no recibe OCR implícito;
- conocimiento general no es fuente corporativa y no produce citas internas;
- el contrato extractivo puede rechazar paráfrasis correctas y aumentar la
  abstención documental; requiere evaluar utilidad y soporte factual con RH;
- el resumen privado cubre la conversación, no un selector de archivo;
- Qwen puede tardar varios minutos si Ollama lo ejecuta parcialmente en CPU.

Parámetros RAG y ubicación exacta en código:
[`RAG_DESIGN.md`](RAG_DESIGN.md).
