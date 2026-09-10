<!-- Creado por Aldo Garcia. -->

# app/llm/

Capa de modelos locales.

| Archivo | Contenido |
|---|---|
| `ollama_client.py` | Adapter Ollama y fábrica pública conservada |
| `provider.py` | Interface InferenceClient y fachada Ollama/API compatible/Vertex |
| `model_policy.py` | Clasificación de intención y router de modelos |

## Cliente único

Ningún otro módulo abre conexiones HTTP hacia Ollama. Un solo punto para
timeouts, reintentos, keep-alive, métricas y preflight.

La fachada ModelClient hace un único intento HTTP; 429/503 no activan fallback.
El adapter OllamaClient directo conserva reintentos configurables (por defecto
cero) para compatibilidad. Sólo un 404 permite probar el modelo alternativo.

El cliente envía `keep_alive=15m`, reutiliza conexiones HTTP (20 totales, 10 en
keep-alive, conexión acotada a 10 s) y mantiene un LRU de 256 embeddings. La
clave de caché es modelo + revisión/digest + SHA-256; no conserva la pregunta en texto.

## Verificación de dimensión

`embed()` comprueba la longitud real de **cada** vector. Si no coincide con la
configurada, lanza `EmbeddingDimensionMismatchError`. **Nunca se trunca ni se
rellena.**

## Modelos

`gemma4:latest` (rápido), `qwen3.6:latest` (profundo), `embeddinggemma:latest`
(embeddings) son los defaults. Se cambian mediante `.env`. Cloud permanece
bloqueado por `LLM_LOCAL_ONLY=true`; Vertex requiere una excepción explícita.

| Perfil | `num_ctx` | `num_predict` | Uso |
|---|---:|---:|---|
| Gemma | 8 192 | 768 | ruta normal y mapas de resumen |
| Qwen | 32 768 | 2 048 | análisis/comparativas y reduce de resumen largo |

Gemma es el modelo predeterminado. Qwen se activa sólo por señales deterministas
del router: profundidad explícita, longitud, varias preguntas/categorías, flujo
multiherramienta, baja confianza, intención mixta o resumen grande. Si un modelo
devuelve HTTP 404, se intenta el modelo alternativo configurado; no se duplica
un error de transporte ni un 503. Los protocolos/configuración están descritos
en [`../../../docs/MODEL_PROVIDERS.md`](../../../docs/MODEL_PROVIDERS.md).

Las intenciones `identity`, `document_summary`, `documental`, `structured`,
`mixed`, `conversational` y `general` mantienen separadas la identidad, la
capacidad general y los turnos documentales. El contrato completo está en
[`../../../docs/AI_DESIGN.md`](../../../docs/AI_DESIGN.md).
