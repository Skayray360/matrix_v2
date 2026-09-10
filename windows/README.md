<!-- Creado por Aldo Garcia. -->

# windows/

Scripts PowerShell que usan los `.bat` de la raíz. **La lógica de negocio no vive
aquí**: estos scripts delegan en los módulos Python del backend.

| Script | Papel | Lanzador `.bat` |
|---|---|---|
| `Common-MatrixRH.ps1` | Funciones compartidas: rutas, Python, Ollama, salud, WAMP | — |
| `Install-MatrixRH.ps1` | Instalación idempotente en 10 pasos | `INSTALAR_MATRIX_RH.bat` (instala **e inicializa**: al terminar encadena `Start-MatrixRH.ps1`) |
| `Start-MatrixRH.ps1` | Preflight, arranque, espera a `/health` y `/ready`, navegador | `INICIAR_MATRIX_RH.bat` |
| `Stop-MatrixRH.ps1` | Detención ordenada; sólo procesos de este proyecto | `DETENER_MATRIX_RH.bat` |
| `Diagnose-MatrixRH.ps1` | Diagnóstico de **solo lectura** | `DIAGNOSTICO_MATRIX_RH.bat` |
| `Validate-MatrixRH.ps1` | Validación completa con evidencia | — (ejecutar por PowerShell) |
| `Install-Autostart.ps1` | Autoarranque opcional por tarea programada | — (`INSTALAR_MATRIX_RH.bat -WithAutostart`) |

## Por qué esta separación

El diagnóstico que ve el operador en Windows es exactamente el que ejecutan las
pruebas: ambos llaman a `scripts.preflight`.

## Flujo consolidado 1.2.1

La entrada corta `install.bat` conserva la cadena original:
`INSTALAR_MATRIX_RH.bat` instala mediante PowerShell y, únicamente si obtiene
código 0, ejecuta `Start-MatrixRH.ps1`. El resultado exitoso exige `/health`,
`/ready` y la interfaz compilada. No hay que ejecutar un segundo instalador.

### Prerrequisitos del servidor

1. Windows con PowerShell 5.1+, Python **3.12 x64** y **uv 0.12.8** en PATH.
   La versión de uv es exacta; el instalador admite sus formatos de salida con
   y sin fecha/target. Python x64 se comprueba ejecutando el intérprete.
2. MySQL/MariaDB activo y una cuenta con los permisos necesarios para crear la
   base nueva y aplicar `backend/migrations`. Configure `DATABASE_URL` en `.env`
   si su servidor difiere del ejemplo. WAMP es una opción para proporcionar MySQL;
   **PHP y Apache no son dependencias del backend FastAPI**. Sus versiones y
   puertos dependen del proxy corporativo que TI decida utilizar.
3. Ollama y los modelos declarados en `.env`, o los runtimes locales alternativos
   configurados mediante los adapters. El instalador comprueba inventario y
   dimensión real de embeddings; no descarga modelos ni sustituye endpoints.
4. Para compilar la UI: **Node.js 22.12+ y Corepack** disponibles por un canal
   autorizado. Corepack usa la versión y el hash real de `packageManager` en
   `frontend/package.json`; `npm ci` utiliza el lockfile sin scripts de instalación.
   Con el build incluido en el ZIP se puede ejecutar `install.bat -SkipFrontend`
   y omitir Node/Corepack en el servidor destino.

### Ejecución

```bat
install.bat
```

Se conserva `.env` si existe. En la primera instalación se copia `.env.example`
y se genera una clave de firma nueva. Las rutas parten de la carpeta del proyecto,
incluidas las carpetas con espacios. Si se copió un `.venv` de otra ubicación, el
instalador lo conserva como `.venv.previous-<fecha>` y crea uno válido para la
ubicación nueva. Estos respaldos no entran en el ZIP de distribución.

La comprobación de MySQL es de lectura y comparte la verificación de propiedad
con el migrador: exige versiones/checksums de Matrix. Nunca se adopta en silencio
una base ajena, aunque esté vacía. Si el nombre está ocupado, se busca un nombre
que **no exista**, y se actualiza únicamente `DATABASE_URL`. Las credenciales no
se pasan al proceso auxiliar mediante argumentos visibles en la línea de comandos.

| Opción | Comportamiento |
|---|---|
| `-SkipFrontend` | Reutiliza `frontend/dist`; falla si falta la interfaz. |
| `-SkipIngest` | Omite la ingesta inicial; no demuestra que el corpus esté indexado. |
| `-Offline` | uv/npm solo usan caché y se desactiva la red de Corepack. Requiere preparar antes todos los paquetes, el gestor y los modelos para Windows x64. El ZIP de fuente no incluye esas cachés. |
| `-WithAutostart` | Registra la tarea del usuario únicamente después de instalar correctamente. Un fallo al registrarla se devuelve como error. |

Para siguientes arranques, diagnóstico y detención:

```bat
INICIAR_MATRIX_RH.bat
DIAGNOSTICO_MATRIX_RH.bat
DETENER_MATRIX_RH.bat
```

El arranque valida que un proceso existente pertenezca a esta carpeta. Si un
arranque nuevo falla, solo se detiene el proceso propio y se limpia su PID.
El diagnóstico `--read-only` no abre Qdrant embebido: informa explícitamente que
esa comprobación se omitió para evitar crear archivos o adquirir el lock del
backend activo. La salud efectiva del índice activo se consulta en `/ready`.

### Evidencia y límites de validación

Se ejecutan contratos Python sobre selección del paquete, lockfiles e integridad,
diagnóstico del adapter y protección de Qdrant en modo de lectura. `bash -n`
comprueba el equivalente Linux. El job `windows-contract` del workflow contiene
el análisis de sintaxis PowerShell y la prueba del BAT en una ruta con espacios.
**Estos contratos no equivalen a una instalación integral en Windows con MySQL,
Ollama y GPU.** Consulte `reports/FINAL_CONSOLIDATION_VALIDATION.md` para conocer
qué pruebas se ejecutaron realmente en esta entrega.
