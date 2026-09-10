<!-- Creado por Aldo Garcia. -->

# app/ingestion/

Ingesta de conocimiento corporativo y de adjuntos privados.

| Archivo | Contenido |
|---|---|
| `loaders.py` | Extractores por formato con límites anti-abuso |
| `isolated_extraction.py` | Extracción en proceso separado con límites de tiempo, RSS y salida |
| `service.py` | Pipeline extract → chunk → embed → upsert → manifest |
| `reconciler.py` | Reconciliación incremental por SHA-256 con lock |

El corpus permanente sigue el contrato descrito en
[`data/knowledge/README.md`](../../../data/knowledge/README.md): documentación
`general` para el perfil base y dominios `especializadas` con ACL propia. Los
adjuntos de chat nunca se escriben en ese árbol; viven en un namespace privado
`user_id + conversation_id`.

## Idempotencia

Se reutiliza sólo si coinciden SHA-256, estado, versión y huella de indexación.
La huella incluye modelo/revisión de embeddings, endpoint, dimensión, plantillas,
chunking y extractor. Se escribe una nueva generación antes de activarla en SQL;
el reconciliador limpia versiones anteriores después del commit. La versión
1.1.0 borraba antes de escribir, lo que podía perder evidencia válida ante un fallo.

## Manifest

Es la propia base interna (`documents` + `document_versions`), no un JSON en
disco: la reconciliación necesita consultas por SHA y por ruta, y un archivo
suelto se desincroniza en cuanto dos procesos escriben a la vez.

## Seguridad de la extracción

Sin macros, sin fórmulas, sin contenido incrustado. Límites de páginas, hojas,
filas, celdas y ratio de descompresión. Un PDF sin capa de texto genera un aviso
explícito; **no se inventa contenido**.

La versión 1.2.1 conserva el orden de párrafos y tablas DOCX. Cambia la versión
del pipeline a 5 y la revisión del extractor a 3: los documentos anteriores
requieren reingesta. No hay OCR, `.doc` binario ni lector `.pptx` implícitos.
Un fallo previo al commit puede dejar puntos nuevos invisibles en Qdrant;
monitorizar espacio y limpiar huérfanos mediante mantenimiento controlado.

Un archivo listo para consultar o resumir debe tener estado `indexed`. `empty`
significa que no produjo texto utilizable; `failed` conserva un mensaje seguro
para diagnóstico.
