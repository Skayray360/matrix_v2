# Proveedores y modelos — Matrix RH 1.2.3

> Creado por Aldo Garcia. Configuración operativa única: `.env`.

## Resultado de la auditoría

El código base ya parametrizaba modelos Ollama, contexto y límite de salida;
no todo estaba hardcodeado. Faltaba abstraer el protocolo y centralizar las
 temperaturas de perfiles/planner, top_p y prefijos de embeddings. La búsqueda
sobre el commit base **no encontró un módulo Vertex/Gemini ni responseSchema**.
Se incorporó el adapter solicitado y su contrato; no se afirma haber validado un
módulo avanzado externo que no está en este repositorio.

`InferenceClient` define el contrato usado por agentes, ingesta y recuperación.
`ModelClient` traduce ese contrato a cada proveedor. Se conserva el nombre
`get_ollama_client()` por compatibilidad, pero devuelve la fachada. Ninguna ruta
de negocio construye `/chat/completions`, `generationConfig` o `responseSchema`.

| Parámetro | Configuración |
|---|---|
| Protocolo rápido / profundo / embeddings | `LLM_PROVIDER`, `LLM_DEEP_PROVIDER`, `LLM_EMBEDDING_PROVIDER` |
| Modelos rápido / profundo / embeddings | `OLLAMA_FAST_MODEL`, `OLLAMA_DEEP_MODEL`, `OLLAMA_EMBEDDING_MODEL` (nombres conservados también para otros adapters) |
| Endpoint Ollama | `OLLAMA_BASE_URL` |
| Endpoint API compatible y credencial | `LLM_API_BASE_URL`, `LLM_API_KEY` |
| Endpoint Vertex | `LLM_VERTEX_BASE_URL`, credenciales ADC administradas por TI |
| Temperatura por tarea | `LLM_TEMPERATURE`, `LLM_GENERAL_TEMPERATURE`, `LLM_SUMMARY_TEMPERATURE`, `LLM_RETRY_TEMPERATURE`, `LLM_PLANNER_TEMPERATURE` |
| Muestreo | `LLM_TOP_P`, `LLM_FAST_TOP_K`, `LLM_DEEP_TOP_K` (top_k opcional) |
| Thinking local | `LLM_FAST_THINKING`, `LLM_DEEP_THINKING`, `LLM_STRUCTURED_THINKING`: `default`, `enabled`, `disabled` |
| Contexto y salida por perfil | `OLLAMA_FAST_NUM_CTX`, `OLLAMA_DEEP_NUM_CTX`, `OLLAMA_FAST_MAX_TOKENS`, `OLLAMA_DEEP_MAX_TOKENS`, `LLM_PLANNER_MAX_TOKENS` |
| Prefijos de entrada | `LLM_SYSTEM_PREFIX`, `LLM_QUERY_TEMPLATE`, `LLM_DOCUMENT_TEMPLATE` |
| Digest y revisión | `LLM_FAST_DIGEST`, `LLM_DEEP_DIGEST`, `LLM_EMBEDDING_DIGEST`, `LLM_EMBEDDING_REVISION` |
| Timeout y admisión | `LLM_REQUEST_DEADLINE_SECONDS`, `CHAT_MAX_INFLIGHT`, `INFERENCE_MAX_INFLIGHT` |

Las políticas de autorización y las instrucciones de negocio permanecen en su
ubicación actual. La serialización de chat templates pertenece al runtime y su
tokenizer. Matrix envía roles/contenido, no tokens especiales de Gemma/Llama.
La API compatible debe implementar chat completions, embeddings e inventario
`/models`; un runtime con API arbitraria necesita un nuevo adapter de
infraestructura, sin cambiar negocio. No se promete compatibilidad universal.

## Cambio Gemma → Llama en Ollama

Instale previamente pesos aprobados de Llama en el runtime. Cambie únicamente
`OLLAMA_FAST_MODEL` y, si aplica, su digest/contexto/límite en `.env`. Reinicie
Matrix y ejecute preflight. Cambiar sólo el generador no obliga a reindexar.
Un cambio de nombre sin instalar pesos termina en error: no descarga modelos
ni sustituye silenciosamente el embedding configurado.

## Cambio de runtime local

Ejemplo: un servidor local compatible con OpenAI expone Llama como `llama-internal`.

```dotenv
LLM_PROVIDER=openai_compatible
LLM_DEEP_PROVIDER=openai_compatible
LLM_API_BASE_URL=http://127.0.0.1:8080/v1
OLLAMA_FAST_MODEL=llama-internal
OLLAMA_DEEP_MODEL=llama-internal
LLM_EMBEDDING_PROVIDER=ollama
LLM_LOCAL_ONLY=true
```

Embeddings pueden permanecer en Ollama para conservar el RAG. Si también se
mueven, configure `LLM_EMBEDDING_PROVIDER=openai_compatible`, el nombre real,
`LLM_EMBEDDING_REVISION` inmutable, ambas dimensiones y prefijos compatibles;
reingiera el corpus. La huella incluye revisión/digest, modelo, endpoint,
plantillas, dimensión, chunking y versión del pipeline. Si cambia la dimensión,
use **nombres nuevos de colecciones** y reingiera: no se borran colecciones
incompatibles automáticamente.

`num_ctx` se envía a Ollama. En la API compatible/Vertex la ventana efectiva la
configura el servidor/modelo; esas APIs no ofrecen el mismo parámetro por
request. TI debe aprovisionar una ventana al menos igual al presupuesto del
perfil. La configuración de Matrix no modifica la VRAM ni el límite del servidor.
Los prefijos `{text}` y `{title}` son placeholders de formato, no código Python.

## Salida estructurada

Desde 1.2.3 el perfil FAST/DEEP viaja separado del nombre del modelo. Un mismo
checkpoint conserva dos presupuestos, sin recargar otro modelo para cambiar de
perfil. `default` omite thinking; `enabled`/`disabled` requieren soporte del
runtime: Ollama recibe `think` y API compatible `chat_template_kwargs.enable_thinking`.
Para schema, `LLM_STRUCTURED_THINKING` puede sobreescribir la elección del perfil.
top_k es opcional; estas opciones locales no se envían silenciosamente a Vertex.
Los delimitadores de reasoning sin procesar se rechazan, incluso si el bloque
está vacío. La respuesta final nunca se reconstruye desde trazas internas.

El planner reserva catálogo, schema, prefijo y salida dentro del presupuesto
FAST estimado; si no cabe, no invoca el modelo ni recorta el contrato. No sustituye
el tokenizer del runtime. Consulte [los tres modelos futuros](LOCAL_MODEL_READINESS.md)
y [la sonda local](MODEL_SMOKE_TEST.md), que no certifica calidad RH.

| Adapter | Solicitud | Comprobación común |
|---|---|---|
| Ollama | `format=<JSON Schema>` | JSON válido y validación completa Draft 2020-12 |
| API compatible local | `response_format.type=json_schema` | Mismo schema y Pydantic de dominio |
| Vertex | `responseMimeType=application/json`, `responseSchema` | Misma validación local después de normalizar la respuesta |

El planner usa `StructuredQueryPlan.model_json_schema()`. Vertex expande refs
locales, convierte los tipos y maneja nullable; campos no soportados producen
error de configuración. `additionalProperties` se valida localmente aunque no
se envíe al subset de Vertex. Salidas vacías, truncadas, con tipos incorrectos o
JSON inválido no entran a SQL ni se aceptan como schema correcto. No hay
reparación heurística que convierta un fallo de parseo en plan autorizado.

En 1.2.1 el schema declara expresamente los escalares/listas permitidos en
valores de filtros; el contrato de los adapters no depende de un campo `Any`
vacío que Vertex no puede interpretar. También se rechazan respuestas Ollama
incompletas/truncadas y embeddings con booleanos, texto o valores no finitos.
La validación de forma no convierte una respuesta válida en verdad factual.

## Vertex opcional

Requiere `LLM_LOCAL_ONLY=false`, `LLM_DEEP_PROVIDER=vertex`, modelo real en
`OLLAMA_DEEP_MODEL`, endpoint HTTPS terminado en `/publishers/google/models` y
el extra Python `vertex` (`uv sync --frozen --extra vertex`). El instalador base
no instala ese extra: aprovisionarlo explícitamente es parte de habilitar cloud.
ADC necesita permiso `aiplatform.endpoints.predict`, API y región/modelo válidos;
no se incorporan claves al repositorio. El cliente refresca el token mediante
google-auth. Preflight/readiness hacen una generación sintética mínima de
conectividad, cacheada cinco minutos por proceso; esa sonda puede generar coste.

**Vertex envía prompts/evidencia a cloud y no cumple el perfil 100% local.**
Mantener el adapter preparado no lo activa. La alternativa para la salida
estructurada es Ollama o un runtime local con JSON Schema soportado.

## Evidencia y límites

`tests/unit/test_implementation_v2.py` cambia exclusivamente un archivo temporal
`.env` entre dos ejecuciones contra transportes HTTP controlados y valida el
mismo resultado estructurado. Otras regresiones cubren dimensiones/orden de
embeddings, RAG real sobre Qdrant local, SQL, citas y rechazo de cloud. Esto prueba
el contrato, no la calidad del nuevo modelo: el SLO y el golden set deben correrse
con pesos, cuantización y hardware reales tras cada cambio.

Un 429/503 no dispara fallback; un HTTP 404 específico del modelo permite el
fallback configurado. No hay retry automático del POST de la fachada. El
presupuesto de tiempo se comparte entre llamadas de la consulta; un runtime
puede continuar computando una solicitud que Matrix ya descartó. Cancelar la
publicación no equivale a detener el kernel GPU.

Los digests opcionales deben fijarse antes de aceptar producción. Para API
compatible la revisión la administra TI; `/models` no demuestra un hash de los
pesos. `:latest` por sí solo no identifica un artefacto reproducible.

[Vertex: formato y subset de schema](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/control-generated-output),
[Ollama: formato de Modelfile y templates](https://docs.ollama.com/modelfile).
