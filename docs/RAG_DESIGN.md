# Diseño del RAG — Matrix RH

> Creado por Aldo Garcia.

Este documento describe el RAG **tal como está implementado**. Cada parámetro
indica el archivo y la clase donde vive, para que documentación y código no
puedan divergir. El mismo conjunto se expone en runtime en
`GET /api/v1/admin/diagnostics` (requiere permiso `diagnostics.read`).

Actualizado para la consolidación 1.2.1. La comparación y los límites de la
entrega se describen en [FINAL_CONSOLIDATION.md](FINAL_CONSOLIDATION.md).

---

## 1. Parámetros efectivos

| Parámetro | Valor | Dónde vive en el código |
|---|---|---|
| `RAG_VECTOR_STORE` | `qdrant` | `backend/app/config/settings.py::Settings.rag_vector_store` |
| `RAG_CHUNK_SIZE_TOKENS` | `900` | `Settings.rag_chunk_size_tokens` |
| `RAG_CHUNK_OVERLAP_TOKENS` | `120` | `Settings.rag_chunk_overlap_tokens` |
| `RAG_EMBEDDING_DIMENSION` | `768` | `Settings.rag_embedding_dimension` |
| `RAG_TOP_K` | `6` | `Settings.rag_top_k` |
| `RAG_FETCH_K` | `24` | `Settings.rag_fetch_k` |
| `RAG_MIN_SIMILARITY` | `0.35` | `Settings.rag_min_similarity` |
| `RAG_MMR_LAMBDA` | `0.65` | `Settings.rag_mmr_lambda` |
| `RAG_SEARCH_STRATEGY` | `cosine_hnsw_metadata_filter_mmr` | `Settings.rag_search_strategy` |
| `RAG_REINDEX_INTERVAL_HOURS` | `24` | `Settings.rag_reindex_interval_hours` |
| Modelo de embeddings | `embeddinggemma:latest` | `Settings.ollama_embedding_model` |
| Modelo rápido | `gemma4:latest` | `Settings.ollama_fast_model` |
| Modelo profundo | `qwen3.6:latest` | `Settings.ollama_deep_model` |
| `OLLAMA_FAST_NUM_CTX` | `8192` | `Settings.ollama_fast_num_ctx` |
| `OLLAMA_DEEP_NUM_CTX` | `32768` | `Settings.ollama_deep_num_ctx` |
| `OLLAMA_FAST_MAX_TOKENS` | `768` | `Settings.ollama_fast_max_tokens` |
| `OLLAMA_DEEP_MAX_TOKENS` | `2048` | `Settings.ollama_deep_max_tokens` |
| `OLLAMA_KEEP_ALIVE` | `15m` | `Settings.ollama_keep_alive` |
| `OLLAMA_EMBEDDING_CACHE_SIZE` | `256` | `Settings.ollama_embedding_cache_size` |
| `OLLAMA_SUMMARY_PARALLEL_BATCHES` | `2` (compatibilidad; mapas actualmente secuenciales) | `Settings.ollama_summary_parallel_batches` |
| `RAG_SUMMARY_SCAN_MAX_CHUNKS` | `256` | `Settings.rag_summary_scan_max_chunks` |
| `RAG_SUMMARY_MAX_CHUNKS` | `24` | `Settings.rag_summary_max_chunks` |
| Margen de baja confianza | `0.05` sobre `RAG_MIN_SIMILARITY` | `backend/app/rag/retriever.py::LOW_CONFIDENCE_MARGIN` |
| Corte estructural por encabezado | `80` tokens mínimos | `backend/app/rag/chunking.py::HEADING_BREAK_MIN_TOKENS` |
| Versión del pipeline | `5` | `backend/app/ingestion/service.py::INGESTION_VERSION` |
| Revisión del extractor en la huella | `3` | `backend/app/rag/index_manifest.py::indexing_fingerprint` |

Estos son valores predeterminados, no el inventario de un servidor desplegado.
Los proveedores, modelos, plantillas y parámetros de inferencia se seleccionan
en `.env`; véase [MODEL_PROVIDERS.md](MODEL_PROVIDERS.md).

### Validaciones que impiden el arranque

Implementadas en `Settings._validate_rag_invariants`:

- `chunk_size > overlap`
- `fetch_k >= top_k`
- `top_k >= 1` (por tipo `Field(ge=1)`)
- `0 <= mmr_lambda <= 1`
- `RAG_EMBEDDING_DIMENSION == OLLAMA_EMBEDDING_DIMENSION`
- `RAG_SUMMARY_SCAN_MAX_CHUNKS >= RAG_SUMMARY_MAX_CHUNKS`

Y en runtime, la fachada `ModelClient.embed` y el adapter `OllamaClient.embed`
comprueban la dimensión **real** de cada
vector. Si no coincide lanza `EmbeddingDimensionMismatchError`. **Nunca se trunca
ni se rellena un vector.**

---

## 2. Vector store

**Qdrant**, por cinco razones funcionales concretas:

1. **Persistencia** en disco entre reinicios.
2. **Búsqueda por coseno** nativa.
3. **Filtros de metadata evaluados dentro del motor**, lo que permite aplicar la
   ACL *antes* de que ningún chunk salga hacia el LLM. Ésta es la razón
   determinante: un vector store sin filtros obligaría a recuperar primero y
   filtrar después, que es exactamente lo que la política prohíbe.
4. **Colecciones separadas** para corpus corporativo y adjuntos privados.
5. **Operación local** y contenerizable.

### Modos

| Modo | Uso | Configuración |
|---|---|---|
| `embedded` (por defecto) | Almacenamiento local persistente del cliente oficial de Qdrant. Sin Docker. | `QDRANT_MODE=embedded`, `QDRANT_PATH=./var/qdrant` |
| `server` | Instancia Qdrant dedicada por HTTP. | `QDRANT_MODE=server`, `QDRANT_URL`, `QDRANT_API_KEY` |

**No existe fallback silencioso.** Si el modo configurado no está operativo,
`VectorStore.health()` falla, `/ready` devuelve 503 y las consultas RAG devuelven
`qdrant_unavailable`.

> **Limitación conocida del modo `embedded`**: el almacenamiento local admite un
> único proceso. Mientras el backend esté arriba, un script que acceda
> directamente al índice fallará con un mensaje explícito. Por eso
> `windows\Validate-MatrixRH.ps1` ejecuta las pruebas directas **antes** de levantar el
> backend para los E2E. Con `QDRANT_MODE=server` esta limitación desaparece.

El cliente embedded realiza búsqueda exacta local; la etiqueta histórica
`RAG_SEARCH_STRATEGY=cosine_hnsw_metadata_filter_mmr` no lo convierte en HNSW.
En modo servidor, `VectorStore.ensure_collection` crea los índices de payload
para filtros de alcance, categoría, propietario, conversación, documento,
generación y huella. El perfil objetivo de concurrencia usa Qdrant servidor
interno y exige mediciones con el corpus real.

### Colecciones

| Colección | Contenido | ACL |
|---|---|---|
| `matrix_rh_corporate` | Conocimiento corporativo | filtro por `scope=corporate` + `category IN (...)` |
| `matrix_rh_private` | Adjuntos de conversación | filtro por `scope=conversation` + `owner_user_id` + `conversation_id` |

---

## 3. Metadata de cada chunk

Definida en `backend/app/rag/schemas.py::ChunkMetadata`:

`chunk_id`, `document_id`, `document_sha256`, `filename`, `relative_path`,
`category`, `subpath`, `mime_type`, `page_or_sheet`, `section`, `chunk_index`,
`text`, `embedding_model`, `embedding_dimension`, `ingestion_version`,
`allowed_roles`, `allowed_groups`, `sensitivity`, `scope`, `owner_user_id`,
`conversation_id`, `generation`, `index_fingerprint`, `created_at`, `updated_at`.

El `source_id` citable se compone como `categoria/archivo#indice`.

---

## 4. Filtros de autorización

`VectorStore.build_corporate_filter(categorias_autorizadas)` construye siempre
una lista **enumerada** de categorías. Incluso el rol administrativo con wildcard
llega aquí con su lista ya resuelta por `PolicyEngine.effective_categories`:
**nunca se consulta sin filtro**.

Si el usuario no tiene ninguna categoría autorizada, el filtro usa una condición
imposible (`category = "__none__"`) en lugar de omitirse. Omitir un filtro vacío
es el error clásico que convierte una restricción en acceso total.

---

## 5. Pipeline de ingesta

```
discover -> authorize policy metadata -> extract -> normalize
   -> structural split -> chunk -> embed -> upsert -> manifest -> verify
```

Implementado en `backend/app/ingestion/service.py::IngestionService._index_document`.

**Orden crítico vigente**: escribir una generación nueva y comprobar el número
de chunks reconocido por la escritura; después activar esa generación mediante
el commit del manifest SQL. Las consultas filtran generación activa y huella
antes del ranking y comprueban de nuevo la visibilidad al convertir resultados.
La generación anterior se conserva hasta confirmar el cambio. El reconciliador
retira las generaciones antiguas con `index_cleanup_pending`.

La versión 1.1.0 borraba antes de insertar; se conserva aquí la causa del cambio:
un fallo de escritura dejaba sin evidencia válida al documento. No existe una
transacción ACID conjunta MySQL–Qdrant. Un fallo previo al commit puede dejar
puntos nuevos invisibles pendientes de mantenimiento; no se afirma que la
recogida de todos los huérfanos esté implementada.

### Manifest

El manifest es la propia base interna:

- `documents` — estado actual: SHA-256, número de chunks, estado, versión del
  pipeline, generación activa, huella e indicador de limpieza pendiente.
- `document_versions` — histórico de reindexados.

Se eligió la base de datos frente a un JSON en disco porque la reconciliación
necesita consultas por SHA y por ruta, y un archivo suelto se desincroniza en
cuanto dos procesos escriben a la vez.

---

## 6. Extracción por formato

| Formato | Estrategia | Límites |
|---|---|---|
| `.docx` | Conserva títulos (nivel de heading), subtítulos, listas, tablas y orden. Las tablas se serializan en Markdown. | — |
| `.md` | Preserva headings, listas y bloques semánticos. | 20 MB |
| `.pdf` | Texto por página. Una página sin capa de texto genera un **aviso explícito**; no se inventa contenido. | 500 páginas |
| `.txt` | Detección de encoding (`utf-8-sig`, `utf-8`, `cp1252`, `latin-1`) con fallback tolerante. | 20 MB |
| `.xlsx` | Por hoja: conserva el nombre de la hoja y los encabezados; cada fila se serializa como `columna: valor`. | 50 hojas, 5000 filas/hoja, 100 columnas |
| `.csv` | Detección de delimitador + mismo formato `columna: valor`. | 20 000 filas |

**No se ejecutan macros, fórmulas ni contenido incrustado.** `openpyxl` se abre
con `data_only=True`, que lee el valor cacheado y nunca evalúa la fórmula
(verificado en `tests/unit/test_loaders.py::TestXlsx::test_no_evalua_formulas`).

### Limitación de PDF sin texto

Un PDF escaneado sin OCR produce `warnings` del tipo
`"Paginas sin texto extraible (posible escaneo sin OCR): 1, 2, 3"` y el documento
queda en estado `empty` si ninguna página produce texto. Si sólo algunas páginas
son ilegibles, se indexa el texto restante y se conserva el aviso; no debe
interpretarse como lectura íntegra. OCR, `.doc` binario y `.pptx` no están
implementados. Los parsers se ejecutan en un proceso separado con límites de
tiempo, RSS y salida; esto limita recursos, no constituye un sandbox de SO.

---

## 7. Chunking

Prioridad de separadores:

1. **Encabezados / secciones** — frontera dura.
2. Párrafos.
3. Listas (agrupadas como un bloque).
4. Tablas / filas (agrupadas como un bloque).
5. Fallback por tokens (frases, luego palabras).

Un encabezado **abre chunk nuevo** aunque el actual no esté lleno, siempre que se
hayan acumulado al menos `HEADING_BREAK_MIN_TOKENS` (80). Esta regla se añadió
tras medir el corpus real: sin ella, un documento de política de 600 tokens caía
en **un único chunk** y su embedding quedaba diluido entre temas distintos. Con
la regla, el mismo corpus pasó de 6 a 24 chunks y la similitud de la mejor
coincidencia subió de ~0.29 a 0.40-0.72.

Esos números se conservan como observación histórica de construcción, no como
benchmark repetido para 1.2.1 ni como umbral transferible a otro modelo/corpus.

Una lista corta o un procedimiento breve **no se parten** si caben dentro del
tamaño máximo.

### Estimación de tokens

El chunking usa una aproximación determinista (`palabras × 1.3`), no el
tokenizador real. Es reproducible, pero no demuestra que cada entrada quepa en
la ventana del modelo: hay que medir corpus, idioma y tokenizador efectivos.
El ensamblado del prompt aplica además un presupuesto conservador y mantiene
unidades completas de evidencia; no recorta una regla para que parezca caber.

---

## 8. Prefijos de tarea de embeddinggemma

`embeddinggemma` es un modelo instruido: espera prefijos distintos para consulta
y documento (`backend/app/rag/embedding_prompts.py`).

| Uso | Plantilla |
|---|---|
| Consulta | `task: search result \| query: {texto}` |
| Documento | `title: {sección o archivo} \| text: {texto}` |

Sin estos prefijos, consulta y documento caen en regiones distintas del espacio
vectorial. Síntoma medido durante la construcción: la pregunta *"con qué
frecuencia se realizan los simulacros"* no recuperaba el párrafo que dice
literalmente *"los simulacros se realizan de forma trimestral"*.

Los prefijos se configuran en `.env` con `LLM_QUERY_TEMPLATE` y
`LLM_DOCUMENT_TEMPLATE`. Son parte de `indexing_fingerprint`, junto con
modelo/revisión, protocolo/endpoint, dimensión, chunking y versión de extracción.
Un cambio invalida la reutilización aun cuando el SHA del documento no cambie.
Cambiar sólo el generador no obliga a reindexar; cambiar embeddings sí.

---

## 9. Recuperación

Orden implementado en `backend/app/rag/retriever.py::Retriever.retrieve`:

1. Resolver identidad y permisos (ya vienen en el `UserContext` firmado).
2. Determinar categorías autorizadas (`PolicyEngine.effective_categories`).
3. Crear la consulta semántica (embedding con prefijo de query).
4. Recuperar `fetch_k` en Qdrant **con el filtro de permisos y `score_threshold`**.
5. Eliminar duplicados y chunks casi equivalentes (`deduplicate`).
6. Aplicar MMR (`maximal_marginal_relevance`); en comparativas conserva el conjunto
   de candidatos para la selección diversa.
7. Preservar diversidad por categoría cuando la pregunta es comparativa
   (`enforce_category_diversity`), antes del corte final.
8. Devolver como máximo `top_k` entre corporativo y privado.
9. Entregar scores y `source_id` al Agente de Conocimiento.

La reformulación de la consulta **nunca** es evidencia.

El pipeline entregado no incluye BM25/búsqueda híbrida, cross-encoder,
multi-query ni ensamblado de chunks vecinos. MMR reduce redundancia, pero no es
un verificador semántico ni un reranker entrenado. Esas extensiones requieren
evaluación separada; no se activan implícitamente en la consolidación.

---

## 10. Resumen de adjuntos por metadata

`Retriever.retrieve_attachment_summary` usa una ruta distinta de la búsqueda
semántica. Una petición como «Resume esto» no describe el contenido, así que un
embedding de esa frase podría quedar bajo el umbral aun cuando el archivo esté
correctamente indexado.

`VectorStore.list_private_chunks` pagina mediante `scroll` y aplica dentro de
Qdrant las tres condiciones obligatorias:

```text
scope = conversation
owner_user_id = usuario autenticado
conversation_id = conversación actual
```

No se genera embedding, no se usa `score_threshold` y no se consulta el corpus
corporativo en esta primera etapa. El límite de scan es 256 chunks; se pide uno
adicional para saber si hubo truncamiento y comunicarlo.

Los chunks se ordenan por archivo e índice. Si el material cabe en el contexto
del modelo elegido, se resume en una llamada. Si no, se particiona en lotes de
hasta 24 chunks y presupuesto de contexto: el perfil rápido procesa los lotes
secuencialmente y el profundo integra los parciales conservando citas. Comparten
deadline y cupos de inferencia del proceso; no se crea un ejecutor por resumen.
El reduce, los parciales y el fallback extractivo pasan por verificación de
fuentes y unidades completas; el fallback tampoco recorta una condición.

Si la conversación no tiene evidencia privada, una solicitud de resumen puede
continuar con búsqueda corporativa autorizada para casos como «resume la política
de vacaciones». No mezcla adjuntos de otra conversación o usuario.

---

## 11. Grounding

El prompt separa cuatro bloques que no se mezclan
(`backend/app/agents/prompts.py`):

| Bloque | Delimitador | Papel |
|---|---|---|
| Pregunta del usuario | `PREGUNTA DEL USUARIO:` | lo que se responde |
| Memoria conversacional | `<<<MEMORIA_CONVERSACION>>>` | contexto de diálogo, **no** evidencia factual |
| Evidencia documental | `<<<EVIDENCIA_DOCUMENTAL>>>` | única base factual documental |
| Resultados estructurados | `<<<RESULTADOS_ESTRUCTURADOS>>>` | única base factual de datos |

`verify_grounding` (en `backend/app/rag/grounding.py`) comprueba la allowlist de
evidencia documental **y estructurada**. La validación extractiva exige una
unidad completa recuperada o una fila SQL completa identificada por columnas;
rechaza substrings que omiten sujeto, negación o condición. Política anti-loop:
**una** sola regeneración. En la consulta documental, dos respuestas rechazadas
terminan en insuficiencia, conservando el contrato de GitHub: una copia de texto
autorizado no demuestra que responda a la pregunta. Sólo la ruta de resumen
puede usar el fallback extractivo verificado con unidades completas.

`citations_valid` describe fuentes permitidas y `extractive_verified` describe
fidelidad textual. `factual_verified` permanece falso: no hay un verificador
semántico calibrado ni una garantía de exactitud del documento original.
`grounded` es un resultado del contrato del verificador, no una certificación
del 100 % de veracidad. Una paráfrasis correcta puede rechazarse y aumentar la
abstención; se acepta esa limitación conservadora hasta contar con una evaluación
real de soporte factual y pertinencia de la respuesta.

---

## 12. Actualización cada 24 horas

`backend/app/jobs/scheduler.py` lanza `reconcile_with_lock` cada
`RAG_REINDEX_INTERVAL_HOURS`. La reconciliación
(`backend/app/ingestion/reconciler.py`):

1. recorre recursivamente el knowledge root;
2. detecta carpetas nuevas → nuevas categorías con deny-by-default;
3. detecta archivos nuevos;
4. detecta archivos modificados **por SHA-256** (no por fecha: copiar un archivo
   cambia la fecha sin cambiar el contenido);
5. detecta archivos eliminados;
6. reindexa sólo lo necesario;
7. elimina los chunks obsoletos;
8. evita reindexar una ruta sin cambios y con versión/huella vigentes; no es
   deduplicación global de copias del mismo archivo en rutas distintas;
9. actualiza el manifest;
10. registra resultados y errores en `ingestion_jobs`.

La consolidación también reconcilia adjuntos privados existentes al cambiar
versión/huella. Conserva ID del documento, propietario y conversación, verifica
el SHA almacenado y resuelve el archivo bajo
`UPLOAD_STORAGE_ROOT/<owner>/<conversation>/<nombre-interno>`; no lee una ruta
absoluta arbitraria del servidor anterior. Para migrar hay que copiar los
adjuntos junto con la BD. Archivos ausentes o modificados se informan como fallo
del job; no se reemplazan silenciosamente ni se duplican mediante otra carga.
`ReconcileStats` separa `private_scanned`, `private_reindexed` y
`private_unchanged`. Los fallos se identifican como `private:<document_id>` con
un error seguro, sin nombre ni contenido del archivo. El registro del job se
confirma antes del primer archivo para que su fallo y rollback no borren la
trazabilidad. Una huella privada incompatible tampoco pasa al resumen por scroll.

El job es idempotente y usa un lock cooperativo en `job_locks` con expiración,
que también cubre el caso de dos procesos distintos.

Los `README.md` de las carpetas de conocimiento se excluyen de la ingesta: son
documentación del repositorio, no conocimiento corporativo.

---

## 13. Evaluación del RAG

Golden set sintético en `backend/tests/rag_eval/golden_set.yaml` (36 casos):
prestaciones, nómina, reclutamiento, relaciones laborales, salud ambiental,
comparativas, preguntas sin respaldo y preguntas restringidas.

Métricas producidas por `backend/scripts/rag_eval.py`:

- `retrieval_hit_rate_pct` — aciertos de casos documentales según su referencia
  esperada; en modo `--full` el resultado incorpora también la generación.
- `source_correctness_pct` — comparación con fuentes esperadas en los casos que
  las declaran; `null` si no hay casos medibles. No equivale a ausencia de fuga ACL.
- `recall_at_k` y `mrr` — cobertura y posición de fuentes esperadas cuando se
  dispone de esa referencia.
- En modo `--full`, la evaluación incorpora generación; el resultado de
  grounding debe interpretarse como contrato extractivo, no juicio semántico.
- `unsupported_claim_rate_pct` — casos sin respaldo en los que el sistema afirmó algo.
- `acl_leakage_rate_pct` — **debe ser 0** en los casos evaluados.

Criterio histórico del golden set: **≥98 %** de casos y **0** fugas ACL.
Ese conjunto sintético es una regresión; aprobarlo no certifica calidad con
políticas reales, ausencia universal de errores ni capacidad de 200–250 usuarios.

Desde la raíz del proyecto:

```bat
set "PYTHONPATH=%CD%\backend"
.venv\Scripts\python.exe -m scripts.rag_eval --retrieval
```
```bat
set "PYTHONPATH=%CD%\backend"
.venv\Scripts\python.exe -m scripts.rag_eval --full --output reports\tests\rag_eval.json
```
