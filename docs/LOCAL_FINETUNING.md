# Fine-tuning local: decisión y comparación

> Creado por Aldo Garcia. Matrix RH 1.2.0 — 2026-09-09.

**Decisión actual: no iniciar entrenamiento. Mantener RAG y medir la versión
corregida. Si después existe una brecha de comportamiento demostrada, utilizar
Unsloth local con QLoRA para un único piloto.** No usar fine-tuning para almacenar
políticas de RH, nómina o permisos por usuario dentro de los pesos.

## Datos disponibles y lo que falta

| Evidencia del repositorio | Consecuencia |
|---|---|
| Generador predeterminado `gemma4:latest`, profundo `qwen3.6:latest`, embeddings `embeddinggemma:latest` | La etiqueta no revela variante, parámetros, cuantización ni digest instalados |
| Golden set de 36 casos sintéticos | Útil para regresión, insuficiente para estimar calidad empresarial o entrenar/evaluar sin contaminación |
| Fallos reproducidos en ACL, validación factual, recuperación y routing | Son defectos de código/datos; modificar pesos no corrige esas causas |
| Documentos RH por categorías con revocación y cambios de versión | RAG permite actualizar fuente y permisos; los pesos no ofrecen revocación documental por usuario |
| Sin dataset de entrenamiento curado ni benchmark del modelo desplegado | No hay ganancia observada ni ROI demostrable de fine-tuning |
| Sin inventario vigente CPU/GPU/VRAM/RAM, digest y throughput de entrenamiento | No se puede asignar duración o factibilidad al servidor destino |

La posible GPU de 16 GB mencionada en documentación histórica debe confirmarse;
no se usa como inventario medido. En particular, no se presupone que Gemma 4 sea
un 4B, ni que un MoE tenga coste de entrenamiento igual a sus parámetros activos.
Ejecutar `python -m scripts.model_inventory` antes de dimensionar.

## Comparación: tres frameworks que entrenan sin cloud

Todos necesitan pesos, tokenizer, dependencias y dataset disponibles en disco.
Desactivar integraciones remotas de tracking; fijar versiones en un entorno de
entrenamiento separado. Ninguno obliga a usar notebooks alojados.

| Criterio | Unsloth | Axolotl | LLaMA-Factory |
|---|---|---|---|
| Gemma actual | Documenta Gemma 4 y variantes E2B/E4B/12B/26B-A4B/31B; confirmar variante y arquitectura de texto/visión del artefacto | Guía específica Gemma 4, ejemplos LoRA/QLoRA y particularidades de attention/KV sharing | Documentación consultada lista Gemma/2/3/3n; **no se confirma Gemma 4** en esa lista. Bloquea la aceptación con el modelo actual hasta probar soporte |
| Hardware/VRAM | QLoRA 4-bit reduce memoria; no hay un mínimo único aplicable a la etiqueta del proyecto. Probar una variante pequeña en GPU de 16 GB sólo después de medir contexto, batch y optimizer | Ejemplos oficiales: Gemma 4 E2B vision LoRA registra ~10.4 GiB y 31B dense QLoRA ~25.2 GiB, ejecutados en GPU de 80 GB. El ejemplo 26B MoE usa 1×80 GB. No interpretar estos picos como garantía para otra config | Tabla general estima QLoRA 4-bit: 7B ~6 GB, 14B ~12 GB, 30B ~24 GB. Son orientaciones generales, **no requisitos validados para Gemma 4** |
| Dataset mínimo viable | No existe mínimo mágico del framework. Piloto propuesto: 500–2,000 ejemplos curados de comportamiento más evaluación separada | Mismo criterio de datos; YAML no compensa un dataset débil | Mismo criterio; UI facilita preparar formato, no crea evidencia de calidad |
| Tiempo en Matrix | Desconocido sin calibración; usar fórmula común de abajo. No reutilizar claims de velocidad del proveedor como benchmark local | Desconocido; attention, longitud y paralelismo cambian el coste | Desconocido; además falta validar compatibilidad exacta |
| Mantenimiento | Medio: fijar Unsloth, CUDA, PyTorch, Transformers y base; repetir exportación/serve al actualizar | Alto para este equipo: más knobs y excepciones Gemma 4 en attention, target modules y kernels | Medio por configuración/UI, pero alto mientras no se confirme Gemma 4 |
| Encaje | Piloto pequeño centrado en formato, estilo y abstención, con evaluación controlada | Adecuado cuando se necesita configuración avanzada/multigpu y personal LLM ops | Adecuado para familias ya soportadas y operación por UI; no primera elección con esta base |

Los valores de VRAM de **inferencia** de una guía no se reutilizan como VRAM de
**entrenamiento**: faltan gradientes, optimizer, activaciones y longitud efectiva.
No se recomienda 31B/26B sobre una supuesta tarjeta de 16 GB sin medición.

### Duración: estimación explícita, no benchmark inventado

Supuesto ilustrativo común: 1,000 ejemplos, 1,024 tokens medios y 3 épocas =
3,072,000 tokens procesados. Con **throughput hipotético**, no medido, de
50–300 tokens de entrenamiento/s, el cálculo da **2.8–17.1 horas**, o
**3.4–20.5 horas** al añadir 20% de evaluación/guardado. No hay datos para ordenar
los tres frameworks por tiempo real. Esta banda no incluye curación ni descarga.

Antes de aprobar un trabajo, ejecutar 50–100 pasos con batch, acumulación,
longitud y cuantización finales; medir tokens/s, tiempo/step y pico de VRAM.
Calcular `tokens_totales / tokens_por_segundo_medido + evaluación + checkpoints`.
Si hay OOM, ajustar la configuración y repetir esa calibración. No entrenar en
la GPU que atiende el chat de producción durante una prueba de capacidad.

### Ollama Modelfile no es un cuarto entrenador

Modelfile define modelo base, parámetros, plantilla y adapters importados. No
implementa un optimizer ni un bucle de entrenamiento. Importar un LoRA ya
entrenado no es fine-tuning nativo. La exportación desde el framework hacia el
runtime debe comprobar compatibilidad de arquitectura y formato por separado.
[Referencia oficial de Modelfile](https://docs.ollama.com/modelfile).

## Por qué Unsloth y qué habilita el piloto

Unsloth tiene soporte documentado de Gemma 4 y una ruta local QLoRA orientada a
pilotos. Axolotl añade complejidad específica que este proyecto todavía no
necesita; LLaMA-Factory no acredita la familia actual en la evidencia revisada.
La recomendación no depende de promesas comerciales de velocidad.

1. Crear un conjunto de evaluación reservado con al menos 200 consultas
   empresariales autorizadas: documento correcto, versión, categoría/rol,
   respuesta verificable, abstención y seguimientos. Es una propuesta de piloto,
   no un mínimo universal ni garantía estadística. Mantener documentos/temas del
   holdout fuera de entrenamiento y controlar duplicados.
2. Medir en baseline corregido Recall@k/MRR, fuente correcta, exactitud factual,
   abstención, fugas ACL y p95 por tarea. Mantener la prueba de carga separada de
   la evaluación de contenido.
3. Clasificar errores. Evidencia ausente o equivocada → corpus/retrieval.
   ACL, citas, cálculo, schema y transacciones → código. Sólo errores persistentes
   de comportamiento con evidencia correcta justifican el piloto de pesos.
4. Comparar mismo modelo base, mismo RAG, mismo hardware y decoding: base contra
   adapter. Reportar aciertos pareados e incertidumbre, latencia, VRAM, coste de
   curación y mantenimiento; no aceptar una mejora de promedio que empeore ACL.
5. Adoptar únicamente si hay mejora medida en el holdout y ningún deterioro
   crítico. Cero fugas observadas es una condición de prueba, no una garantía de
   seguridad universal. Si la ganancia no compensa el coste, conservar el base.

**No hay hoy datos que demuestren beneficio proporcional del entrenamiento.**
Eso permite decidir no gastar todavía; no permite afirmar que el RAG actual ya
alcanzó la calidad o la capacidad objetivo.

## Fuentes primarias, consultadas 2026-09-09

- [Unsloth: Gemma 4 y fine-tuning](https://unsloth.ai/docs/models/gemma-4).
- [Axolotl: Gemma 4, configuraciones y memoria observada](https://docs.axolotl.ai/docs/models/gemma4.html).
- [LLaMA-Factory: modelos y estimaciones de hardware](https://github.com/hiyouga/LlamaFactory).
- [LLaMA-Factory: instalación local](https://llamafactory.readthedocs.io/en/latest/getting_started/installation.html).
