# Preparación de los tres modelos locales solicitados

> Creado por Aldo Garcia. Revisión de fuentes primarias: 2026-09-10.

## Alcance y decisión

Matrix conserva su arquitectura, autenticación y RAG. Los tres candidatos se
integran mediante el adapter `openai_compatible`, con un **servidor de inferencia
local separado**. No se descargan pesos, ejecuta código de modelos ni sustituye
el modelo activo durante la instalación de Matrix. Preparar el contrato y probarlo
con respuestas controladas no equivale a certificar el runtime, GPU o calidad.

Para RH en español, el orden propuesto de **evaluación**, no de calidad demostrada,
es Gemma 26B AWQ, Gemma 31B FP8 y Nemotron Omni. El primero reduce el tamaño de
pesos; el segundo permite contrastar calidad con una variante densa; Nemotron
necesita comprobar especialmente el español y aporta modalidades que Matrix
todavía no consume. Conservar el modelo actual hasta completar esta comparación.

## Identidad: un nombre abreviado no identifica los pesos

Los siguientes repositorios coinciden con los nombres solicitados. Las dos
cuantizaciones Gemma son publicaciones de terceros sobre Google Gemma, no pesos
cuantizados publicados por Google. TI debe aprobar también al publicador.

| Candidato | Identificador comprobado | Revisión observada, no activada |
|---|---|---|
| Gemma 31B FP8 dinámico | [RedHatAI/gemma-4-31B-it-FP8-dynamic](https://huggingface.co/RedHatAI/gemma-4-31B-it-FP8-dynamic) | `d4ab4f579dd3516f97d8a6a4c98d0653480bad15` |
| Gemma 26B A4B AWQ 4-bit | [cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit](https://huggingface.co/cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit) | `180b2d35e35e4e48f6245367f3b41036f7cdabd6` |
| Nemotron Omni, BF16 | [nvidia/Nemotron-3-Nano-Omni-30B-A3B-Reasoning-BF16](https://huggingface.co/nvidia/Nemotron-3-Nano-Omni-30B-A3B-Reasoning-BF16) | `e5e9932441de940c9a62185c870ea5bcd4cd24e2` |
| Nemotron Omni, FP8 | [nvidia/Nemotron-3-Nano-Omni-30B-A3B-Reasoning-FP8](https://huggingface.co/nvidia/Nemotron-3-Nano-Omni-30B-A3B-Reasoning-FP8) | `0acd4b1c237eab45d3977b1b46631919e9a75774` |
| Nemotron Omni, NVFP4 | [nvidia/Nemotron-3-Nano-Omni-30B-A3B-Reasoning-NVFP4](https://huggingface.co/nvidia/Nemotron-3-Nano-Omni-30B-A3B-Reasoning-NVFP4) | `16993199e436da4ba75ddc410855f87e0d996ee6` |

Las revisiones se consultaron mediante la API pública de metadatos de Hugging
Face; no son SHA-256 de archivos. En destino se necesita además el inventario
SHA-256 de los archivos efectivamente aprovisionados, tokenizer, plantilla y
digest de la imagen del runtime. Un alias servido en `/v1/models` tampoco prueba
la identidad binaria de los pesos.

El nombre `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` identifica también el
producto/API de NVIDIA. **No configurar su endpoint público** como alternativa:
enviaría información fuera de Matrix. La ficha muestra una opción NIM local,
pero sus contenedores, licencias y aprovisionamiento constituyen otro despliegue
que debe aprobar TI. [Producto NVIDIA](https://build.nvidia.com/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning).

## Arquitectura, memoria y compatibilidad

| Candidato | Arquitectura / formato real | Condición de despliegue |
|---|---|---|
| Gemma 31B FP8 | Denso; `Gemma4ForConditionalGeneration`; `compressed-tensors`, pesos FP8 por canal y activaciones FP8 dinámicas por token; algunas capas conservan BF16 | vLLM con kernels compatibles; no es un archivo GGUF ni un AWQ intercambiable |
| Gemma 26B AWQ | MoE, aproximadamente 25.2B totales y 3.8B activos; `compressed-tensors`, enteros de 4 bits empaquetados, grupos de 32, capas excluidas en FP16 | Probar la combinación concreta Gemma4 MoE + compressed-tensors + GPU; no imponer `--quantization awq` solamente por el nombre del repositorio |
| Nemotron Omni | Backbone híbrido Mamba2–Transformer MoE, aproximadamente 3B activos, más encoders visual/audio; FP8/NVFP4 usan `modelopt` | NVIDIA documenta vLLM 0.20.0 y código personalizado; Linux, CUDA 13.0 o variante CUDA 12.9, según imagen/GPU |

La arquitectura Gemma y su contexto máximo de 262144 tokens se contrastaron con
[Google](https://huggingface.co/google/gemma-4-31B-it); las cuantizaciones con
[configuración FP8](https://huggingface.co/RedHatAI/gemma-4-31B-it-FP8-dynamic/raw/d4ab4f579dd3516f97d8a6a4c98d0653480bad15/config.json)
y [configuración AWQ](https://huggingface.co/cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit/raw/180b2d35e35e4e48f6245367f3b41036f7cdabd6/config.json).
La [receta vLLM Gemma 31B](https://recipes.vllm.ai/Google/gemma-4-31B-it)
menciona 0.19.1+ para la familia; esto **no certifica una versión mínima exacta
para todo checkpoint AWQ**. Aprobar una versión/digest concreta después de las
pruebas. No instalar nightly ni usar índices `unsafe-best-match` en Matrix.

| Pesos | Tamaño de artefactos / dato oficial | Interpretación para hardware |
|---|---|---|
| Gemma 31B FP8 | Dos shards suman **33268122536 bytes**, unos 33.27 GB decimales | No cabe completamente en 16 GB; falta reservar KV cache, buffers y memoria del runtime |
| Gemma 26B AWQ | Publicador: **17.19 GB**; índice: **17186571212 bytes** | No prometer funcionamiento íntegro en una GPU de 16 GB; 24 GB es un candidato de laboratorio, no un mínimo validado aquí |
| Nemotron BF16 | NVIDIA indica H100 de **80 GB** como mínimo de su configuración | No extrapolar a una GPU doméstica por tener sólo 3B activos |
| Nemotron FP8 | NVIDIA indica L40S de **48 GB** como mínimo | Depende también del contexto y modalidades |
| Nemotron NVFP4 | NVIDIA indica RTX 5090 de **32 GB**; otras plataformas específicas soportadas | NVFP4 no equivale a AWQ ni garantiza soporte en generaciones de GPU anteriores |

Fuentes: [metadatos de shards FP8](https://huggingface.co/api/models/RedHatAI/gemma-4-31B-it-FP8-dynamic?blobs=true),
[publicador AWQ](https://huggingface.co/cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit),
[hardware publicado por NVIDIA](https://huggingface.co/nvidia/Nemotron-3-Nano-Omni-30B-A3B-Reasoning-BF16).
El índice FP8 consultado declara un `total_size` distinto a la suma de shards;
para dimensionar la transferencia se usó la suma de archivos, no ese metadato.
Ningún tamaño de disco sustituye una medición de VRAM residente bajo carga.

La matriz general de vLLM diferencia kernels FP8 W8A8 de AWQ/Marlin y sus
arquitecturas GPU. Tener memoria suficiente no garantiza soporte del kernel.
[Compatibilidad de cuantización de vLLM](https://docs.vllm.ai/en/latest/features/quantization/).

No importar directamente estos checkpoints FP8/AWQ con `ollama create` suponiendo
compatibilidad. Una variante GGUF aprobada para Ollama sería **otro artefacto**, con
otra cuantización y evaluación. Ollama documenta importación de formatos concretos,
no conversión universal de cualquier checkpoint. [Importación Ollama](https://docs.ollama.com/import).

## Razonamiento, español y salida estructurada

Gemma4 utiliza `enable_thinking`; el template deja thinking desactivado por
defecto. NVIDIA lo activa por defecto y su ficha declara soporte lingüístico
**English only**: no presentar a Nemotron como modelo validado para RH español.
Ambos necesitan su parser de salida: `gemma4` o `nemotron_v3`, respectivamente.
[Gemma y sus roles](https://huggingface.co/google/gemma-4-31B-it),
[comportamiento Nemotron](https://huggingface.co/nvidia/Nemotron-3-Nano-Omni-30B-A3B-Reasoning-FP8).

El contrato de Matrix conserva únicamente la respuesta final. Los campos
`reasoning` y el anterior `reasoning_content` no son la respuesta ni se deben
reenviar como historial. El runtime debe separar el razonamiento; un contenido
con delimitadores sin procesar se rechaza en lugar de convertirlo heurísticamente
en una respuesta. [Separación de campos vLLM](https://docs.vllm.ai/en/latest/features/reasoning_outputs/).

Controles operativos en `.env`:

| Variable | Uso |
|---|---|
| `LLM_FAST_THINKING`, `LLM_DEEP_THINKING` | `default`, `enabled` o `disabled`; `default` conserva el comportamiento previo y omite la opción |
| `LLM_STRUCTURED_THINKING` | Mismos valores; permite desactivar thinking para peticiones con schema, aunque el perfil profundo lo active |
| `LLM_FAST_TOP_K`, `LLM_DEEP_TOP_K` | Opcionales; no introducir un muestreo distinto en modelos existentes sin configurarlo |

Los presets futuros empiezan con thinking desactivado, incluido JSON. Después,
comparar `enabled` en preguntas complejas, aumentando el presupuesto de generación
y midiendo la respuesta final. Thinking consume tokens, tiempo y memoria: si el
modelo agota `max_tokens` antes de terminar, la respuesta se rechaza. La
configuración no cambia automáticamente por encontrar la palabra `Reasoning`.

La recomendación de Google (`temperature=1.0`, `top_p=0.95`, `top_k=64`) es una
referencia de su modelo, no evidencia de que mejore este RAG. NVIDIA proporciona
un perfil instruct con temperatura 0.2 y top_k 1. Mantener las temperaturas por
tarea documentadas en [MODEL_PROVIDERS.md](MODEL_PROVIDERS.md) hasta contrastar
ambas configuraciones con el mismo corpus. No subirlas globalmente por el nombre.

El planner continúa usando `StructuredQueryPlan`, `response_format=json_schema`
y validación local completa. Un servidor que acepte chat pero rechace el schema
**no está listo para Matrix**. No convertirlo silenciosamente en JSON libre, ni
confundir el parser de tool calls con validación de planes SQL autorizados.

## Aprovisionamiento seguro, separado de la instalación de Matrix

1. Confirmar GPU, VRAM libre, arquitectura, driver, RAM y sistema operativo
   actuales. El inventario histórico de 16 GB no demuestra capacidad actual.
2. TI aprueba publicador, licencia, revisión de pesos, tokenizer, template y
   versión/digest del runtime. Para Nemotron revisar el código personalizado
   antes de permitir `trust_remote_code`; safetensors no elimina ese riesgo.
3. Aprovisionar una copia local inmutable y escanear las dependencias del runtime
   separado. No instalar vLLM, CUDA, torch ni código de modelos dentro del venv
   de Matrix; `npm audit` y `pip-audit` de Matrix no auditan ese contenedor.
4. Mantener el servicio en loopback o una red de TI autorizada, sin publicar
   puertos ni rutas de archivos arbitrarias. No usar
   `--allowed-local-media-path /`, `--privileged` o montajes amplios del servidor.
5. Desactivar telemetría (`VLLM_NO_USAGE_STATS=1`) y aplicar bloqueo de salida
   en el firewall del runtime; precargar también todos sus archivos auxiliares.
   Las variables offline no son una política de firewall.
6. Ejecutar **un candidato a la vez**. Las rutas siguientes son ejemplos y deben
   apuntar a la copia aprobada de la revisión correspondiente.

[Opt-out de telemetría vLLM](https://docs.vllm.ai/en/latest/usage/usage_stats/).

### Gemma 31B FP8: ejemplo de servicio Linux local

El runtime ya debe estar instalado, auditado y cualificado por TI. No se ejecutó
este comando en el entorno de revisión.

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 VLLM_NO_USAGE_STATS=1 \
vllm serve /srv/matrix-models/gemma31-fp8 \
  --served-model-name RedHatAI/gemma-4-31B-it-FP8-dynamic \
  --host 127.0.0.1 --port 8080 \
  --max-model-len 32768 --max-num-seqs 2 \
  --gpu-memory-utilization 0.80 \
  --language-model-only \
  --reasoning-parser gemma4 \
  --default-chat-template-kwargs '{"enable_thinking":false}'
```

El modo sólo lenguaje y parser se basan en el despliegue del
[publicador FP8](https://huggingface.co/RedHatAI/gemma-4-31B-it-FP8-dynamic).
Los límites de contexto, concurrencia y memoria son puntos de partida prudentes
para la prueba, **no ajustes de capacidad certificados**.

### Gemma 26B AWQ: mismo contrato, checkpoint distinto

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 VLLM_NO_USAGE_STATS=1 \
vllm serve /srv/matrix-models/gemma26-awq \
  --served-model-name cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit \
  --host 127.0.0.1 --port 8080 \
  --max-model-len 32768 --max-num-seqs 2 \
  --gpu-memory-utilization 0.80 \
  --language-model-only \
  --reasoning-parser gemma4 \
  --default-chat-template-kwargs '{"enable_thinking":false}'
```

El formato se descubre desde `config.json`, sin forzar otro esquema de
cuantización. Si no arranca con la combinación aprobada, detener la aceptación;
no desactivar comprobaciones ni cambiar automáticamente a pesos distintos.

### Nemotron Omni FP8: ejemplo condicionado a revisión de código

Sólo después de la aprobación expresa de TI para ejecutar el código del
checkpoint local. La referencia oficial exige vLLM 0.20.0; no se instala aquí
ni se interpreta ese requisito como aprobación de seguridad de tal versión.
[Despliegue oficial NVIDIA](https://huggingface.co/nvidia/Nemotron-3-Nano-Omni-30B-A3B-Reasoning-FP8).

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 VLLM_NO_USAGE_STATS=1 \
vllm serve /srv/matrix-models/nemotron-omni-fp8 \
  --served-model-name nvidia/Nemotron-3-Nano-Omni-30B-A3B-Reasoning-FP8 \
  --host 127.0.0.1 --port 8080 \
  --max-model-len 32768 --max-num-seqs 2 \
  --gpu-memory-utilization 0.80 \
  --trust-remote-code \
  --reasoning-parser nemotron_v3 \
  --default-chat-template-kwargs '{"enable_thinking":false}'
```

No se habilitan rutas a medios, herramientas ni entradas multimodales. Matrix
envía texto extraído; tener un modelo Omni **no incorpora OCR, audio o video al
pipeline actual**. La guía de NVIDIA menciona SGLang BF16 y FP8/NVFP4 pendientes;
no sustituir el runtime propuesto por SGLang dando esa compatibilidad por hecha.

## Conectar Matrix sin cambiar negocio

Ejemplo mínimo para el servidor Gemma 26B anterior; usar el identificador servido
exacto de cada candidato en **ambos** campos de modelo cuando sea el único
generador. Esto evita un fallback accidental al modelo anterior.

```dotenv
LLM_LOCAL_ONLY=true
LLM_PROVIDER=openai_compatible
LLM_DEEP_PROVIDER=openai_compatible
LLM_API_BASE_URL=http://127.0.0.1:8080/v1
OLLAMA_FAST_MODEL=cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit
OLLAMA_DEEP_MODEL=cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit
OLLAMA_FAST_NUM_CTX=8192
OLLAMA_DEEP_NUM_CTX=32768
LLM_FAST_THINKING=disabled
LLM_DEEP_THINKING=disabled
LLM_STRUCTURED_THINKING=disabled
LLM_FAST_TOP_K=64
LLM_DEEP_TOP_K=64
LLM_EMBEDDING_PROVIDER=ollama
```

Conservar nombre, revisión/digest, dimensiones y prefijos del embedding actual;
no reindexar por cambiar sólo el generador. Para Nemotron, el punto inicial de
muestreo es top_k 1; los presupuestos de Matrix deben caber dentro del límite
real del servidor. Las revisiones del checkpoint compatible se acreditan con el
manifiesto externo, **no usando un commit de Hugging Face como digest Ollama**.

Los ejemplos no alteran `AUTH_PROVIDER`, ACL, documentos ni credenciales. En una
topología WSL/Docker, `127.0.0.1` no siempre corresponde al host Windows; TI debe
configurar la dirección interna correcta y `LLM_LOCAL_HOSTS`, preservando las
restricciones de red. No abrir el endpoint al exterior para resolver conectividad.

## Puerta de aceptación en destino

- [ ] Verificar que `/v1/models` publica el identificador configurado y que el
  manifiesto corresponde a los archivos ejecutados.
- [ ] Ejecutar [la sonda de inferencia](MODEL_SMOKE_TEST.md) con `--profile all`:
  respuesta numérica sintética, salida `StructuredQueryPlan` y embedding con
  dimensión correcta; guardar resultado junto al inventario del runtime.
  Esta sonda no mide español ni provoca truncación deliberadamente: el rechazo
  de truncados se prueba mediante contratos HTTP simulados.
- [ ] Evaluar por separado respuestas en español y, en el entorno descartable,
  provocar agotamiento del presupuesto para verificar el comportamiento real
  del runtime y el rechazo de salidas incompletas.
- [ ] Con una base y colecciones **descartables**, seguir [E2E.md](E2E.md) y
  [TESTING.md](TESTING.md). Nunca autorizar pruebas destructivas sobre producción.
- [ ] Ejecutar el golden set con el mismo corpus/ACL para cada candidato;
  revisar también paráfrasis, tablas, negaciones y preguntas sin respuesta.
- [ ] Medir latencias p50/p95/p99, tokens de salida, consumo de memoria, tiempo
  en cola y errores con thinking desactivado y después activado sólo donde aporte.
- [ ] Validar una conversación con varios turnos: no aparecen trazas internas
  ni tokens especiales en interfaz, fuentes o historial.
- [ ] Confirmar funcionamiento con salida a Internet bloqueada.
- [ ] Aprobar un ganador con datos de RH en español; conservar rollback del
  `.env` y del runtime anterior. La aprobación de 200–250 usuarios exige otra
  prueba de carga; no se deduce del número de parámetros activos.

Estado de esta revisión: identidad, documentación y contrato preparados; pesos,
drivers, kernels, GPU, calidad y E2E completos con estos candidatos **pendientes
de ejecución en el servidor destino**. Véase también
[LOCAL_MODEL_OPTIMIZATION.md](LOCAL_MODEL_OPTIMIZATION.md).
