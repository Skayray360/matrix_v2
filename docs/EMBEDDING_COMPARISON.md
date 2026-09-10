# Embeddings: conservar EmbeddingGemma y evaluar E5 con el corpus de Matrix

> Creado por Aldo Garcia. Revisión de implementación 1.2.3, 2026-09-10.

## Decisión

**Se conserva `embeddinggemma:latest`, a 768 dimensiones, como embedding por defecto.**
Cambiar entre los tres generadores solicitados no requiere sustituir este modelo
ni reindexar. El generador redacta; el embedding determina qué fragmentos se
recuperan. Sus nombres, pesos y contratos son independientes.

La decisión se sustenta en menor tamaño del modelo, mayor ventana documental,
índices ya compatibles y ausencia de una mejora medida de E5 en Matrix. **No se
afirma que EmbeddingGemma sea más preciso que E5 en español o en RH**: no se han
ejecutado ambos modelos sobre el mismo corpus corporativo y hardware.
Tampoco se instala un segundo runtime de embeddings sin un beneficio demostrado.

## Comparación verificable

| Aspecto | EmbeddingGemma usado por Matrix | `intfloat/multilingual-e5-large` | Consecuencia para Matrix |
|---|---|---|---|
| Tamaño publicado | 308 millones de parámetros | Aproximadamente 0.6 mil millones, según el redondeo de la ficha | Más parámetros no garantizan mejor recuperación. Comparar memoria y rendimiento reales. |
| Entrada máxima | 2,048 tokens | 512 tokens | Los fragmentos actuales de 900 tokens **estimados** no se pueden trasladar a E5 sin revisar su tamaño. |
| Dimensiones | 768; admite reducciones MRL | 1,024 | E5 requiere colecciones nuevas; no rellenar ni recortar vectores para fingir compatibilidad. |
| Multilingüe | Entrenado en más de 100 idiomas | Soporta 100 idiomas | Ninguna cifra de idiomas certifica terminología empresarial mexicana. |
| Consulta | `task: search result \| query: {text}` | `query: {text}` | Aplicar el prefijo del embedding, no el del generador. |
| Documento | `title: {title} \| text: {text}` | `passage: {text}` | No conservar el prompt Gemma al sustituirlo por E5. |
| Despliegue | Disponible localmente; ya integrado con Ollama | Pesos ejecutables en servidor local | El uso de repositorios para aprovisionar pesos no obliga a enviar documentos a servicios cloud. |

Datos de [Google: descripción de EmbeddingGemma](https://ai.google.dev/gemma/docs/embeddinggemma),
[Google: contrato de entrada, dimensiones y prompts](https://ai.google.dev/gemma/docs/embeddinggemma/model_card)
y [Intfloat: ficha oficial de multilingual-e5-large](https://huggingface.co/intfloat/multilingual-e5-large).
Son propiedades de las fichas oficiales; no se han inspeccionado los pesos del
servidor destino ni comprobado que una etiqueta local personalizada los conserve.
Las etiquetas `latest` no identifican una cuantización inmutable: el despliegue
debe registrar el digest realmente instalado y comprobarlo con
`LLM_EMBEDDING_DIGEST`. La huella de indexación usa la revisión real del runtime.

### Coste: estimación, no benchmark del servidor

Con el mismo número de vectores y almacenamiento float32, el vector de 768
dimensiones ocupa 3,072 bytes y el de 1,024 ocupa 4,096: **E5 agrega 33.3 % de
datos vectoriales brutos**. Un millón de vectores equivale a 3.072 frente a
4.096 GB decimales, antes de índices, metadatos, réplicas y memoria de proceso.
Si E5 necesita fragmentos más cortos, también puede aumentar el número de
vectores. Estos cálculos no equivalen al tamaño final de Qdrant.

Como orden de magnitud de **pesos solamente**, 308 millones de parámetros a
16 bits representan 0.616 GB; 0.6 mil millones representan aproximadamente
1.2 GB. No son requisitos mínimos de VRAM: faltan activaciones, lotes,
tokenizador, buffers y runtime; la cuantización cambia la cifra. La memoria y
latencia del servidor de Matrix siguen pendientes de medición. No se extrapola
el resultado de EdgeTPU publicado por Google a una GPU NVIDIA o a Ollama.

### Benchmarks: no mezclar puntuaciones incompatibles

Google publica resultados MTEB **v2**, con promedios por tarea y tipo de tarea.
El [informe original de E5](https://arxiv.org/html/2402.05672v1) presenta MTEB
inglés de 56 conjuntos y MIRACL, incluyendo español. Son protocolos diferentes:
restar esos promedios no demuestra superioridad de uno sobre otro.

`multilingual-e5-large-instruct` es además un modelo diferente de
`multilingual-e5-large`: no transferir sus resultados ni su formato de entrada.
Un ranking general sirve para elegir candidatos, no para certificar fuentes,
permisos, citas o respuestas de RH.

## Contratos revisados en el código real

| Componente | Contrato existente y efecto |
|---|---|
| `backend/app/config/settings.py` | Modelo de embeddings, proveedor, dimensión y plantillas son configurables. Exige que ambas variables de dimensión coincidan. |
| `backend/app/rag/embedding_prompts.py` | Consulta y documento utilizan las plantillas de configuración. Los constantes históricos describen el valor por defecto, no fuerzan el formato al cambiar la configuración. |
| `backend/app/rag/chunking.py` | Estima tokens como palabras × 1.3; no usa el tokenizador de ninguno de los modelos. El límite de fragmento es aproximado. |
| `backend/app/llm/ollama_client.py` | Valida cantidad, dimensión y valores numéricos finitos. Rechazar la truncación de entrada es distinto de validar la longitud del vector de salida. |
| `backend/app/llm/provider.py` | Mantiene el embedding independiente de los modelos rápido/profundo. El runtime compatible requiere revisión identificable y contrato de respuesta. |
| `backend/app/rag/index_manifest.py` | La huella incluye modelo, revisión, proveedor/endpoint, dimensión, plantillas y fragmentación. Cambiar el generador por sí solo no altera la huella. |
| `backend/app/rag/vector_store.py` | Usa coseno y rechaza colecciones de dimensión incompatible. No borra automáticamente el índice anterior. |
| `backend/app/rag/retriever.py` | Usa umbral de recuperación y una señal de baja confianza. Deben calibrarse para la distribución de similitudes del embedding utilizado. |

### Truncación silenciosa: defecto a corregir sin sustituir el embedding

La revisión de 1.2.2 encontró que la llamada a `/api/embed` omitía `truncate`.
La [API oficial de Ollama](https://docs.ollama.com/api/embed) declara `true`
como valor por defecto y admite `false` para rechazar entradas que no caben.
Por tanto, un vector válido de 768 dimensiones podía representar solo el
principio de un fragmento, aunque Qdrant conservara y mostrara el texto completo.

En 1.2.3 se exige **`truncate: false`** en embedding y sonda de dimensión. El
error debe impedir publicar la nueva generación; no se soluciona recortando
silenciosamente el texto o rellenando vectores. También hay que reindexar para
retirar representaciones antiguas que pudieran haber sido truncadas.

Una estimación de 900 tokens no demuestra que el texto, prefijo y título quepan
en 2,048 tokens reales. Códigos largos, tablas, términos técnicos o texto sin
espacios pueden desviarse mucho. La protección detecta el exceso; **no implementa
por sí sola fragmentación exacta por tokenizador**. Un servidor de embeddings
compatible debe rechazar el exceso o aportar un conteo exacto verificable; no
se presupone que una opción específica de Ollama exista en cualquier API.

La normalización no justifica cambiar el índice a producto escalar:
[Qdrant normaliza vectores para coseno](https://qdrant.tech/documentation/manage-data/collections/),
y MMR calcula coseno en el backend. Si se sirve E5, el runtime debe realizar
el pooling enmascarado y la normalización de su implementación oficial; devolver
estados de tokens o aplicar otro pooling no constituye el mismo embedding.

## Si se autoriza probar E5 posteriormente

1. Aprovisionar pesos, tokenizer y runtime aprobados **en un entorno local de
   evaluación separado**, fijando revisiones y cuantización. No instalar pesos
   arbitrarios mediante scripts remotos ni habilitar ejecución de código del
   repositorio del modelo sin revisión.
2. Configurar el nombre servido en `OLLAMA_EMBEDDING_MODEL`, el proveedor y su
   endpoint interno. Para API compatible, fijar `LLM_EMBEDDING_REVISION` a la
   revisión real; los nombres heredados `OLLAMA_*` también se usan con ese adapter.
3. Configurar `OLLAMA_EMBEDDING_DIMENSION=1024`,
   `RAG_EMBEDDING_DIMENSION=1024`,
   `LLM_QUERY_TEMPLATE='query: {text}'` y
   `LLM_DOCUMENT_TEMPLATE='passage: {text}'`. Incluir el título en el documento
   es una variante de representación que debe evaluarse y versionarse.
4. Rehacer la fragmentación con el tokenizer de E5, dejando espacio para
   prefijos y tokens especiales dentro de 512. Valores como 384/64 son solamente
   un punto de partida de tamaño/solape estimados, **no una garantía de cabida**.
   Verificar que no se separen condiciones, excepciones o encabezados de tablas.
5. Crear nombres nuevos de colecciones corporativa y privada; reindexar ambas
   con la nueva huella y validar propietarios, conversaciones y ACL. No ejecutar
   una comparación A/B usando simultáneamente la misma BD mutable de manifiestos:
   su generación activa cambiaría para ambos experimentos. Usar copias de
   evaluación independientes y preservar la combinación original BD/índice.
6. Calibrar `RAG_MIN_SIMILARITY` y la señal de baja confianza. E5 documenta
   similitudes concentradas aproximadamente entre 0.7 y 1.0; reutilizar 0.35
   no equivale a conservar el mismo criterio de relevancia. No importar los
   umbrales de otros proyectos.
7. Aplicar el criterio A/B siguiente antes de promover. La reversión requiere
   configuración y manifiesto de índice coherentes; no basta renombrar el
   modelo conservando vectores de E5.

## Criterio A/B de aceptación propuesto, aún no ejecutado

Separar dos comparaciones: primero **mismos fragmentos** que quepan en ambos
modelos para aislar el embedding; después **cada pipeline optimizado** para
medir el resultado operativo. Registrar extractor, fragmentos, tokenizer,
prefijos, revisión, cuantización, distancia, umbrales y parámetros de búsqueda.

Propuesta inicial: 200 preguntas revisadas por RH, de las cuales 40 sirven para
calibrar y 160 quedan reservadas para aceptación. Es un piloto, no una garantía
estadística de cobertura. Estratificar prestaciones, nómina, permisos, siglas,
negaciones, excepciones, seguimiento conversacional, comparativas y preguntas
sin respuesta. Agregar pruebas ACL independientes, incluyendo revocaciones.

| Medida | Regla de decisión propuesta |
|---|---|
| Recall@6 y nDCG@6 | Medir sobre evidencias anotadas. Exigir mejora de al menos 3 puntos porcentuales en Recall@6 y nDCG sin regresión; reportar intervalo de confianza pareado, no solo promedio. |
| Datos críticos | Ninguna regresión observada en cifras, condiciones, excepciones o permisos del conjunto reservado. Esto no certifica casos no probados. |
| Respuestas y abstención | Mismo generador, prompt y presupuesto para ambas ramas; revisar utilidad, fidelidad, citas y falsas respuestas por separado. |
| Coste operativo | Medir p50/p95/p99, documentos por segundo, tamaño del índice, RAM/VRAM y fallos con chat concurrente. Rechazar una mejora de recuperación que incumpla el SLO acordado. |
| Seguridad | Cero fuga ACL observada, ninguna entrada truncada aceptada y ninguna salida de documentos hacia cloud. |

Los 22 casos respondibles anotados del golden set existente sirven como smoke
test; no sustituyen este corpus reservado. Una diferencia incierta, una ganancia
inferior al umbral o ausencia de medidas mantiene **EmbeddingGemma** como opción
de Matrix. Este umbral es una propuesta de aceptación del proyecto, no una
recomendación de los autores de los modelos.

## Pruebas de contrato incorporadas

`backend/tests/unit/test_embedding_switch_contracts.py` verifica que los tres
nombres de generador no cambian el embedding ni la huella y que un solo archivo
de configuración cambia los prefijos y la dimensión de E5. Utiliza datos
sintéticos, sin descargar pesos. Demuestra aislamiento de configuración, **no
compatibilidad binaria del runtime ni calidad semántica de los modelos**.

Desde `backend`:

```bash
python -m pytest tests/unit/test_embedding_switch_contracts.py -q
```

Para el procedimiento general de selección y medición véase
[optimización de modelos locales](LOCAL_MODEL_OPTIMIZATION.md) y
[contrato de proveedores](MODEL_PROVIDERS.md).
