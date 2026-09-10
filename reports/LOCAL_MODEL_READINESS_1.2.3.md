<!-- Creado por Aldo Garcia. -->
# Validación integrada — instalación y modelos locales 1.2.3

Fecha: 2026-09-10. Base de trabajo: 1.2.2, commit `1b2a9fe`.
Se conservan la base GitHub `94fa083` (1.1.0), revisión `472607f` (1.2.0),
consolidación `6ba83f3` (1.2.1), estructura, documentación histórica y lógica de
autorización/RAG. El commit de esta entrega incluye código y changelog README.

## Dictamen

Preparado **a nivel de configuración y contratos** para los tres modelos
solicitados; no se ejecutaron sus pesos. No certifica compatibilidad binaria del
runtime, VRAM, calidad RH, multimodalidad ni capacidad 200–250. Se conserva
EmbeddingGemma: no hay comparación sobre corpus RH que demuestre una mejora de E5.

La instalación frontend limpia pasa sin lifecycle hooks. No aparecen avisos
conocidos en npm ni en los paquetes Python auditados. Los controles no garantizan
ausencia de malware desconocido, paquetes ofuscados o compromiso previo del host.
El aprovisionamiento de modelos/vLLM/CUDA es independiente: sus dependencias no
quedan auditadas por los resultados de Matrix.

## Pruebas realmente ejecutadas

| Verificación | Resultado | Límite |
|---|---|---|
| Backend unitarias, seguridad e integración | **846 aprobadas, 154 omitidas, 0 fallidas; 1000 recopiladas**, 9.09 s | 153 requieren MySQL/MariaDB ausente; 1 requiere observación `/proc` del proceso hijo |
| Nuevas regresiones | **130 aprobadas**: 34 suministro, 28 perfiles, 22 protocolo, 42 sonda, 4 cambio de embedding | HTTP controlado, SQLite/Qdrant aislados según caso; no pesos reales |
| Frontend Vitest | **29 aprobadas**, 6 archivos | No navegador E2E ni servicios reales |
| Instalación frontend aislada desde lock | 152 paquetes instalados; sin hooks ejecutados; build/typecheck y 29 tests pasan | Ensayo Linux, no Windows |
| Build final | TypeScript + Vite aprobados, versión frontend 1.2.3 | No prueba visual ni del servidor productivo |
| TypeScript E2E explícito | Aprobado | Typecheck no ejecuta los casos |
| Playwright `--list` | **28 casos recopilados**, 4 archivos | No ejecutados: faltan navegador/servicios/modelos de aceptación |
| npm audit completo y producción | **0 vulnerabilidades conocidas**; lock 175 entradas | Consulta a registro el 2026-09-10, no veredicto perpetuo |
| pip-audit del venv | **0 vulnerabilidades conocidas**, 95 paquetes externos auditados | Proyecto editable excluido; 96 entradas totales con Matrix. No incluye extra Vertex ni drivers externos |
| Supply chain lock + árbol | 175 entradas del lock, 152 manifiestos instalados; 0 bloqueos/IOC | Opcionales de otras plataformas explican diferencia; no sumar conteos |
| SAST Bandit sobre `app` | 0 hallazgos | No prueba dinámica de seguridad ni código del runtime/modelo |
| Escáner de secretos | 0 secretos reales | Placeholders/fixtures sintéticos identificados por sus reglas |
| Ruff fuentes/scripts y tests nuevos | Aprobado | Conserva reglas existentes |
| Encabezados de autoría | 310 archivos, aprobado | No modifica atribución original |
| Bash y diff | `bash -n` y `git diff --check` aprobados | PowerShell, Docker y Actions no ejecutados |

Se observó una advertencia Starlette: TestClient con httpx está deprecado;
no hubo fallo ni aviso de vulnerabilidad por ello. También existen advertencias
del entorno npm `http-proxy` y `whatwg-encoding` deprecado, detalladas en el
[informe de suministro](SUPPLY_CHAIN_1.2.3.md). No se cambiaron dependencias
por preferencia estética ni se ejecutó `audit fix --force`.

## Reproducción de validación

Desde `backend/`, primero preparar entorno reproducible:

```bash
uv sync --frozen --extra dev
.venv/bin/python -m pip_audit --skip-editable --format json --output /ruta/segura/python-audit.json
```

En Windows sustituir `.venv/bin/python` por `.venv\Scripts\python.exe`.
La auditoría consulta nombres/versiones al servicio de avisos; se ejecuta en
preparación conectada, no durante inferencia local. El extra `dev` no es un
requisito para operación habitual.

Desde la raíz del proyecto, con servicios de prueba ausentes como aquí:

```bash
backend/.venv/bin/python -m pytest backend/tests/unit backend/tests/security backend/tests/integration --tb=short -o addopts='' --junitxml=/ruta/segura/pytest.xml
backend/.venv/bin/python -m scripts.verify_supply_chain --lock-only
backend/.venv/bin/python -m scripts.verify_supply_chain --json
```

Si MySQL está disponible, antes de ejecutar integración se exige el contrato
de [entorno descartable](../docs/TESTING.md): `APP_ENV=test`, BD/almacenamiento
de prueba y permiso explícito en el entorno de la terminal. **Nunca ejecutar
fixtures destructivos sobre la BD productiva.** Las omisiones de esta revisión
no deben copiarse como aprobaciones en destino.

Para frontend, seguir primero la secuencia segura del informe de suministro.
Después, desde `frontend/`:

```bash
corepack npm run build
corepack npm test
node_modules/.bin/tsc --noEmit --target ES2022 --module ESNext --moduleResolution Bundler --esModuleInterop --skipLibCheck --types node tests/e2e/*.ts playwright.config.ts
corepack npm run e2e -- --list
```

## Decisiones y correcciones verificadas

- FAST/DEEP se mantienen distintos aunque usen el mismo checkpoint. Sus
  presupuestos se transmiten desde el orquestador, incluidos resumen y fallback.
- El planner estima catálogo, schema, pregunta, prefijo y salida antes de
  inferencia; no produce un plan a partir de un catálogo recortado.
- Thinking y top_k son configurables por perfil; no se imponen a modelos ya
  instalados. JSON conserva validación completa del schema de dominio.
- Respuestas sin contenido final, incompletas, con schema inválido o tokens
  de razonamiento sin procesar se rechazan. Se probaron los delimitadores
  reales de Gemma `<|channel>thought…<channel|>`, también vacíos.
- La sonda exige revisión del embedding: inventario y forma vectorial no bastan
  si el RAG no puede construir una huella reproducible. No publica razonamiento,
  respuestas, secretos ni mensajes de excepción.
- Ollama recibe `truncate:false`; la nueva huella registra la política.
  API compatible declara política `runtime_defined`: TI debe verificar el
  rechazo de sobrelongitud, no se supone una opción universal.
- EmbeddingGemma se conserva a 768 dimensiones. Un cambio de generador no
  modifica la huella de indexación; un cambio a E5 sí la modifica y necesita
  fragmentación, prefijos, dimensiones, calibración e índices coherentes.

## Migración y aceptación pendiente

**La actualización a 1.2.3 exige reindexar** por pipeline/ingesta 6, incluso
manteniendo el embedding. Respaldar BD, corpus, adjuntos, configuración e índice
con el servicio detenido; ejecutar instalación sin `-SkipIngest` y revisar
resultados corporativos/privados. No borrar colecciones ni restaurar huellas
antiguas para evitar el control. Ver [reversión](../docs/DEPLOYMENT_V2.md).

Tras aprovisionar un candidato aprobado por TI, usar solamente `.env` para
conectarlo. La [guía de modelos](../docs/LOCAL_MODEL_READINESS.md) documenta
identificadores, revisiones, formatos y hardware; la [sonda](../docs/MODEL_SMOKE_TEST.md)
requiere `--run-inference --profile all`. No usar un endpoint NVIDIA público.
Nemotron requiere revisar su código personalizado y su español, ya que la ficha
declara English only. Los modelos cuantizados no se importan a Ollama por su
nombre sin validar el formato.

Falta ejecutar pesos/GPU, español RH, groundedness semántica, corpus representativo,
E2E real, AD/SSO, instalador Windows completo, Docker y carga 200–250. La guía de
evaluación local de Hugging Face se aplicó para separar smoke/contratos de una
evaluación con pesos; no se usó su alternativa cloud ni se lanzó entrenamiento.
La capacidad, verificación factual y tablas extensas pendientes de 1.2.2 no
quedan resueltas por cambiar de modelo.

El ZIP final contiene fuentes, build de UI, documentación, pruebas, lockfiles,
historial Git y SHA256SUMS. Excluye venv, node_modules, pesos, credenciales y
estado runtime. No se sobrescribe GitHub `main` como parte de esta entrega.
