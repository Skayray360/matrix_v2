# Instalación y aceptación de Matrix RH 1.2.1

> Creado por Aldo Garcia. Este checklist requiere ejecución real por TI.

## Copia a Windows

`install.bat` delega en `INSTALAR_MATRIX_RH.bat` y conserva su orden de
instalación/arranque. Los scripts resuelven rutas desde su propia carpeta y
entrecomillan rutas con espacios. El proyecto no requiere PHP; necesita MySQL
activo, no simplemente una carpeta WAMP instalada.

- [ ] Aprovisionar Python 3.12 x64, uv 0.12.8 x64, Node 22.12+ y Corepack,
  runtime de IA y pesos elegidos, MySQL/MariaDB compatible y espacio para
  dependencias, índice, adjuntos y backups. Verificar procedencia/integridad de
  los instaladores. El instalador no instala servicios privilegiados ni drivers.
- [ ] Preparar `.env` (variables exactas en `.env.example`) con rutas relativas.
  `DATABASE_URL` debe contener credenciales propias; caracteres reservados en el
  DSN se codifican como URL. No compartir `.env` en tickets o repositorio.
- [ ] `QDRANT_MODE=server` y `QDRANT_URL` interno para el perfil de capacidad.
  Aprovisionar Qdrant servidor local y API key si corresponde. Los puertos
  habituales: Matrix 8000 detrás de HTTPS 443; MySQL 3306; Ollama 11434; Qdrant
  HTTP 6333. Sólo exponer el frontend/proxy a los usuarios.
- [ ] Copiar proyecto a una ruta de prueba con espacios. Ejecutar `install.bat`.
  El venv de otro root se aparta y reconstruye, no se confía en ejecutables con
  rutas del servidor anterior. `MATRIX_INSTALL_ROOT` no sustituye los paths de
  Settings; actualizar cualquier ruta absoluta personalizada en `.env`.
- [ ] En destino sin Internet: preparar **caches Windows** de uv/npm y pesos.
  `install.bat -Offline` no puede inventar dependencias ausentes del cache.
  Un build ya validado permite `-SkipFrontend`; no omitirlo con el checkout fuente.
  La compilación usa `corepack npm ci --ignore-scripts` con versión/hash del
  gestor fijados en `frontend/package.json`. `-SkipFrontend` evita requerir
  Node/Corepack sólo si existe `frontend/dist`; `-Offline` desactiva también la
  red de Corepack.
- [ ] Confirmar bootstrap de BD nueva y segunda instalación idempotente. Una
  base ajena nunca se adopta implícitamente; el instalador elige otro nombre o
  exige la opción explícita de adopción. Las migraciones conservan las previas.
- [ ] Confirmar `/health` 200, `/ready` 200 y HTML/JS de la UI, login, chat
  documental con cita, carga privada y publicación administrativa.
- [ ] Detener MySQL, runtime o IdP activo: el diagnóstico/startup debe informar
  fallo y devolver código distinto de cero. Restaurar y comprobar recuperación.
- [ ] Reiniciar Windows y probar el mecanismo de arranque elegido.
  `-WithAutostart` registra inicio de sesión, no un servicio Windows previo al login.

## Actualización desde 1.1.0 o la revisión 1.2.0

1. Detener Matrix. Respaldar BD, `.env`, corpus, adjuntos y Qdrant de forma
   consistente. No copiar un Qdrant embedded abierto.
2. Aplicar código y migraciones `0004_memory_authorization`,
   `0005_index_generations`, `0006_chat_operations` mediante el instalador.
3. Reingerir el corpus. Los chunks anteriores sin generación/huella quedan
   fuera de recuperación hasta reconstruirlos. Un cambio de dimensión requiere
   nuevas colecciones; conservar las previas para recuperación.
   En 1.2.1 `INGESTION_VERSION=5` y extractor 3 invalidan también la extracción
   DOCX de 1.2.0. La revisión de versiones no implica entrenar de nuevo el LLM.
   En 1.2.3 pipeline/ingesta 6 obliga a reconstruir también índices de 1.2.2:
   Ollama rechaza ahora entradas de embedding que exceden su contexto, sin
   truncarlas. Ejecutar `install.bat` sin `-SkipIngest`, o desde `backend/`
   `..\.venv\Scripts\python.exe -m scripts.bootstrap ingest` con servicio detenido
   (venv raíz creado por el instalador Windows).
   La reconciliación procesa corpus y privados. Revisar todos los errores antes
   de habilitar tráfico; no bajar la huella para reutilizar vectores antiguos.
4. Los asistentes/resúmenes históricos sin alcance verificable se ocultan;
   permanecen en SQL para revisión administrada. No asignarles automáticamente
   los permisos actuales: eso restauraría la fuga que se corrigió.
5. Si se trasladan datos: restaurar MySQL y `var/uploads` además de Qdrant y
   corpus. Los paths nuevos se resuelven desde la carpeta; los `storage_path`
   históricos son metadatos, no un mecanismo de copia de archivos.
   Ejecutar la reconciliación y revisar sus fallos: los adjuntos previos se
   reindexan conservando ID, propietario y conversación; se comprueba el SHA
   original y sólo se abre el archivo dentro del root privado restaurado.
   Una ruta absoluta del equipo anterior no autoriza leer fuera de ese root.
   No volver a cargar el adjunto para ocultar una migración fallida.
   Revisar `private_scanned`, `private_reindexed`, `private_unchanged` y errores
   `private:<document_id>` del job. Una extracción fallida conserva el manifest
   anterior; su huella incompatible se mantiene fuera de consultas y resúmenes.
6. Para revertir, detener servicio y restaurar el conjunto compatible de código,
   configuración, BD e índice del backup. No ejecutar 1.1.0 sobre un estado
   parcialmente restaurado ni borrar columnas a mano.

Las generaciones nuevas son invisibles hasta el commit SQL. Una bandera durable
solicita limpiar generaciones anteriores desde el reconciliador. Un fallo previo
al commit puede dejar puntos huérfanos invisibles en Qdrant; monitorizar espacio
y eliminarlos en mantenimiento controlado, nunca purgar la colección activa por
suposición. Es una limitación operativa pendiente de un recolector de huérfanos
completo, no una pérdida de la versión válida.

## Operación y límites

- Un proceso API: cupos iniciales 4 chats, 2 llamadas IA, 1 upload. No aumentar
  workers de Uvicorn esperando multiplicar capacidad: los contadores y límites
  por usuario son por proceso. Embedded admite un único propietario del índice.
- El exceso se rechaza con 503; no existe aún una cola durable distribuida.
  Los IDs de solicitud permiten consultar resultado/estado y solicitar cancelar
  su publicación. El runtime puede continuar generando hasta terminar/timeout.
- El parser se ejecuta en proceso separado con vigilancia de RSS/tiempo/salida.
  Es aislamiento de recursos; no es un sandbox de sistema operativo ni una
  garantía de memoria pico exacta entre muestras del watchdog.
- `/ready` comprueba dependencias, no certifica capacidad ni una sesión SSO real.
- Los informes de release 1.1.0 y `reports/IMPLEMENTATION_V2_VALIDATION.md` se
  preservan como históricos. La comparación y el enlace a la validación final
  están en [FINAL_CONSOLIDATION.md](FINAL_CONSOLIDATION.md).

## Prueba de 200 sostenidos, 250 pico y recuperación

No hay aceptación de capacidad en esta entrega. Ejecutar en un entorno
representativo y aislado, con permisos y datos de prueba. Registrar GPU/VRAM,
CPU/RAM, versiones/digests/cuántización, contexto, corpus, índices y límites.

```bat
set "PYTHONPATH=%CD%\backend"
.venv\Scripts\python.exe -m scripts.model_inventory --output var\reports\model-inventory.json
```

Definir previamente SLO por ruta y longitud de entrada/salida. Preparar al menos
250 **identidades diferentes** con permisos representativos y sus sesiones
reales fuera del repositorio. `sessions.json` es un array privado de
`{"session_token":"...","csrf_token":"..."}`; `prompts.json` contiene preguntas
documentales sintéticas. No usar 250 pestañas de una cuenta: activaría el límite
por usuario y no representaría la población.

```bat
.venv\Scripts\python.exe -m scripts.load_test --base-url https://matrix-pruebas.interno --sessions C:\TI\sessions.json --prompts C:\TI\prompts.json --users 200 --duration 300 --output var\reports\load-200.json
.venv\Scripts\python.exe -m scripts.load_test --base-url https://matrix-pruebas.interno --sessions C:\TI\sessions.json --prompts C:\TI\prompts.json --users 250 --duration 60 --output var\reports\load-250.json
.venv\Scripts\python.exe -m scripts.load_test --base-url https://matrix-pruebas.interno --sessions C:\TI\sessions.json --prompts C:\TI\prompts.json --users 200 --duration 180 --output var\reports\load-recovery.json
```

Agregar `--slo-p95` y `--max-error-pct` con valores aprobados por TI para evaluar
ese gate. Sin umbrales, el reporte dice indeterminado. Las latencias de éxito se
separan de rechazos rápidos; 503/429 cuentan como errores de servicio. El perfil
es de usuarios en ciclo cerrado, no un generador de tasa de llegada constante.
La API no transmite streaming: este script mide latencia completa, no TTFT.

Correlacionar con conexiones SQL activas, CPU/RAM/VRAM, tokens/s del runtime,
latencia Qdrant, cola del runtime y logs de admisión. Repetir con cargas privadas,
resúmenes, consultas SQL, revocación durante inferencia y caída/recuperación de
servicios. El script de chat no ejecuta por sí solo esos escenarios.

Medir calidad factual/fuentes y ACL sobre los resultados por separado. Un
`grounded=true` o una cita presente no es un benchmark semántico. Sólo TI puede
cerrar la aceptación al cumplir conjuntamente latencia, errores, calidad,
seguridad y recuperación; el script no marca `capacity_certified=true`.
