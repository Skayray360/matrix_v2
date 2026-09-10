# Creado por Aldo Garcia.
<#
.SYNOPSIS
    Funciones compartidas por todos los scripts de Windows de Matrix RH.

.DESCRIPTION
    Los archivos .bat de la raiz no contienen logica: llaman a estos scripts, y
    estos delegan el diagnostico y la operacion en el modulo Python
    `scripts.bootstrap` / `scripts.preflight`. Un unico lugar donde vive la
    logica evita que el comportamiento del instalador y el de las pruebas se
    separen con el tiempo.
#>

Set-StrictMode -Version Latest

# Raiz del proyecto: este script vive en <raiz>\windows\
$script:MatrixRoot = Split-Path -Parent $PSScriptRoot
$script:VenvPython = Join-Path $script:MatrixRoot ".venv\Scripts\python.exe"
$script:BackendDir = Join-Path $script:MatrixRoot "backend"
$script:LogDir = Join-Path $script:MatrixRoot "var\logs"
$script:PidFile = Join-Path $script:MatrixRoot "var\matrixrh-backend.pid"

function Get-MatrixRoot { return $script:MatrixRoot }
function Get-MatrixLogDir { return $script:LogDir }
function Get-MatrixPidFile { return $script:PidFile }
function Get-MatrixBackendDir { return $script:BackendDir }

function Test-MatrixOwnedProcess {
    param($Candidate)
    if (-not $Candidate -or -not $Candidate.ExecutablePath -or -not $Candidate.CommandLine) { return $false }
    return ([string]::Equals($Candidate.ExecutablePath, $script:VenvPython, [System.StringComparison]::OrdinalIgnoreCase) -and
        $Candidate.CommandLine -match '(?:^|\s)-m\s+scripts\.bootstrap\s+serve(?:\s|$)')
}

function Stop-MatrixOwnedBackend {
    <# Limpieza de un arranque fallido; no actua sobre un PID reutilizado. #>
    param([int]$ProcessId)
    $candidate = Get-CimInstance Win32_Process -Filter "ProcessId=$ProcessId" -ErrorAction SilentlyContinue
    if (Test-MatrixOwnedProcess $candidate) {
        Stop-Process -Id $ProcessId -ErrorAction SilentlyContinue
    }
    if ((Test-Path $script:PidFile) -and ((Get-Content $script:PidFile -Raw).Trim() -eq [string]$ProcessId)) {
        Remove-Item $script:PidFile -ErrorAction SilentlyContinue
    }
}

function Write-Section {
    param([string]$Text)
    Write-Host ""
    Write-Host ("=" * 72) -ForegroundColor DarkCyan
    Write-Host "  $Text" -ForegroundColor Cyan
    Write-Host ("=" * 72) -ForegroundColor DarkCyan
}

function Write-Step { param([string]$Text) Write-Host "  -> $Text" -ForegroundColor Gray }
function Write-Ok { param([string]$Text) Write-Host "  [ OK ] $Text" -ForegroundColor Green }
function Write-Warn { param([string]$Text) Write-Host "  [WARN] $Text" -ForegroundColor Yellow }
function Write-Fail { param([string]$Text) Write-Host "  [FAIL] $Text" -ForegroundColor Red }

function Test-MatrixVenv {
    return (Test-Path $script:VenvPython)
}

function Get-MatrixPython {
    <#
        Devuelve el interprete a usar. Prioriza el venv del proyecto; si no
        existe, busca Python 3.12 x64 mediante el lanzador `py`.
    #>
    if (Test-MatrixVenv) { return $script:VenvPython }

    $launcher = Get-Command py -ErrorAction SilentlyContinue
    if ($launcher) {
        $candidate = & py -3.12 -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $candidate) { return $candidate.Trim() }
    }
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) { return $python.Source }
    return $null
}

function Assert-Python312 {
    <# Verifica que el interprete sea exactamente 3.12 y de 64 bits. #>
    param([string]$PythonPath)

    if (-not $PythonPath) {
        Write-Fail "No se encontro ningun interprete de Python."
        Write-Host "         Instale Python 3.12 x64 desde https://www.python.org/downloads/"
        return $false
    }
    $info = & $PythonPath -c "import sys,platform; print(f'{sys.version_info.major}.{sys.version_info.minor}|{platform.architecture()[0]}')" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "No fue posible ejecutar el interprete: $PythonPath"
        return $false
    }
    $parts = $info.Trim().Split('|')
    if ($parts[0] -ne "3.12") {
        Write-Fail "Se requiere Python 3.12 (encontrado $($parts[0]))."
        return $false
    }
    if ($parts[1] -ne "64bit") {
        Write-Fail "Se requiere Python 3.12 de 64 bits (encontrado $($parts[1]))."
        return $false
    }
    Write-Ok "Python 3.12 x64: $PythonPath"
    return $true
}

function Invoke-MatrixPython {
    <#
        Ejecuta un modulo Python del backend con el PYTHONPATH correcto.
        Devuelve UNICAMENTE el codigo de salida del proceso.

        La salida del proceso se envia a la consola con Out-Host y no al flujo de
        salida de la funcion: en PowerShell, todo lo que una funcion emite forma
        parte de su valor de retorno, de modo que sin Out-Host el llamador
        recibiria un arreglo con las lineas del diagnostico mas el codigo, y una
        comparacion como `if ($code -ne 0)` seria siempre verdadera.
    #>
    param(
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [switch]$Quiet
    )
    # Los modulos del backend SIEMPRE necesitan las dependencias del proyecto.
    # Sin el entorno virtual, caer al Python del sistema produce un
    # ModuleNotFoundError con traceback que no le dice nada al operador.
    if (-not (Test-MatrixVenv)) {
        if (-not $Quiet) {
            Write-Fail "No existe el entorno virtual del proyecto (.venv)."
            Write-Host "         Ejecute INSTALAR_MATRIX_RH.bat antes de este comando."
        }
        return 126
    }

    $python = Get-MatrixPython
    if (-not $python) { return 127 }

    $previous = $env:PYTHONPATH
    $previousPreference = $ErrorActionPreference
    $env:PYTHONPATH = $script:BackendDir
    try {
        Push-Location $script:BackendDir
        # 'Continue' es imprescindible: PowerShell convierte CUALQUIER escritura a
        # stderr de un ejecutable nativo en un registro de error y la envuelve en
        # un NativeCommandError. Con eso, el mensaje accionable de Python queda
        # sepultado bajo "Traceback (most recent call last)" y el operador no ve
        # la causa real. Aqui stderr se trata como texto normal.
        $ErrorActionPreference = 'Continue'
        if ($Quiet) {
            & $python @Arguments 2>&1 | Out-Null
        }
        else {
            & $python @Arguments 2>&1 | ForEach-Object { Write-Host $_ }
        }
        return $LASTEXITCODE
    }
    finally {
        Pop-Location
        $env:PYTHONPATH = $previous
        $ErrorActionPreference = $previousPreference
    }
}

function Test-MatrixDatabaseFree {
    <#
        Comprueba si una base MySQL esta libre para Matrix RH.

        Devuelve una tabla con Libre = $true si la base no existe o solo contiene
        la tabla de control de Matrix RH; $false si ya tiene tablas de otra
        aplicacion. Es de SOLO LECTURA: no crea ni modifica nada.
    #>
    param(
        [Parameter(Mandatory = $true)][string]$DatabaseUrl,
        [Parameter(Mandatory = $true)][string]$DatabaseName
    )

    # El import va DENTRO del try: si se ejecuta con un interprete sin las
    # dependencias del proyecto, un ImportError a nivel de modulo escaparia como
    # traceback y el llamador lo confundiria con el veredicto.
    $codigo = @"
import json
import re
import sys

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import make_url
    from app.database.migrator import applied_versions, inspect_ownership
except ImportError:
    print('DESCONOCIDO:SinDependencias')
    sys.exit(0)

try:
    arguments = json.loads(sys.stdin.buffer.read().decode('utf-8-sig'))
    nombre = arguments['name']
    if not re.fullmatch(r'[A-Za-z0-9_]{1,64}', nombre):
        raise ValueError('NombreInvalido')
    url = make_url(arguments['url']).set(database='')
    engine = create_engine(url, pool_pre_ping=True, future=True)
    with engine.connect() as conn:
        existe = conn.execute(
            text('SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = :n'),
            {'n': nombre},
        ).first()
        # LIBRE = la base NO existe, asi que Matrix RH puede crearla. Una base
        # que ya existe nunca es 'LIBRE', aunque este vacia: pudo crearla otra
        # aplicacion.
        if not existe:
            print('LIBRE')
            sys.exit(0)
    engine.dispose()
    engine = create_engine(url.set(database=nombre), pool_pre_ping=True, future=True)
    try:
        propia, tablas = inspect_ownership(engine)
        if propia and applied_versions(engine):
            print('PROPIA')
            sys.exit(0)
    finally:
        engine.dispose()
    ajenas = [t for t in tablas if t != 'schema_migrations']
    # Existe pero no es nuestra: vacia o con tablas ajenas, en ambos casos hay
    # que elegir otro nombre.
    print('EXISTE_VACIA' if not ajenas else 'OCUPADA:' + ','.join(sorted(ajenas)[:6]))
except Exception as exc:
    print('DESCONOCIDO:' + type(exc).__name__)
"@

    $temporal = Join-Path $env:TEMP "matrixrh-dbcheck-$([guid]::NewGuid().ToString('N')).py"
    Set-Content -Path $temporal -Value $codigo -Encoding UTF8
    $previousPreference = $ErrorActionPreference
    $previousPythonPath = $env:PYTHONPATH
    $previousEncoding = $OutputEncoding
    try {
        $python = Get-MatrixPython
        if (-not $python) { return @{ Libre = $false; Detalle = 'DESCONOCIDO:SinPython' } }
        $ErrorActionPreference = 'Continue'
        $env:PYTHONPATH = $script:BackendDir
        $OutputEncoding = New-Object System.Text.UTF8Encoding($false)
        # Las credenciales viajan por stdin, nunca en la linea de comandos.
        $payload = @{ name = $DatabaseName; url = $DatabaseUrl } | ConvertTo-Json -Compress
        $salida = ("$($payload | & $python $temporal 2>&1 | Select-Object -Last 1)").Trim()

        # Solo cuatro respuestas son un veredicto. Cualquier otra cosa (una linea
        # de traceback, una advertencia del interprete) significa que NO se pudo
        # determinar, y debe tratarse como tal en lugar de asumir lo peor.
        $veredictos = @('LIBRE', 'PROPIA', 'EXISTE_VACIA')
        if ($veredictos -notcontains $salida -and $salida -notlike 'OCUPADA:*') {
            return @{ Libre = $false; Detalle = "DESCONOCIDO:$salida" }
        }
        # LIBRE  = no existe, Matrix RH la creara.
        # PROPIA = instalacion previa de Matrix RH, se reutiliza.
        # EXISTE_VACIA / OCUPADA = existe y no es nuestra: hay que elegir otro
        #   nombre, aunque este vacia.
        return @{ Libre = ($salida -eq 'LIBRE' -or $salida -eq 'PROPIA'); Detalle = $salida }
    }
    finally {
        $ErrorActionPreference = $previousPreference
        $env:PYTHONPATH = $previousPythonPath
        $OutputEncoding = $previousEncoding
        Remove-Item $temporal -ErrorAction SilentlyContinue
    }
}

function Set-MatrixEnvValue {
    <# Reemplaza una clave del .env conservando el resto del archivo. #>
    param(
        [Parameter(Mandatory = $true)][string]$Key,
        [Parameter(Mandatory = $true)][string]$Value
    )
    $envFile = Join-Path $script:MatrixRoot ".env"
    if (-not (Test-Path $envFile)) { return $false }
    $contenido = Get-Content $envFile
    # No usar Value como reemplazo regex: una contrasena con $1/$& se alteraria.
    $nuevo = foreach ($line in $contenido) {
        if ($line -match "^$([regex]::Escape($Key))=") { "$Key=$Value" }
        else { $line }
    }
    Set-Content -Path $envFile -Value $nuevo -Encoding UTF8
    return $true
}

function Test-MatrixEnvFile {
    <# Crea .env a partir de .env.example la primera vez. Nunca lo sobrescribe. #>
    $envFile = Join-Path $script:MatrixRoot ".env"
    $example = Join-Path $script:MatrixRoot ".env.example"
    if (Test-Path $envFile) {
        Write-Ok "Archivo .env presente (no se sobrescribe)."
        return $true
    }
    if (-not (Test-Path $example)) {
        Write-Fail "No existe .env.example; el paquete esta incompleto."
        return $false
    }
    Copy-Item $example $envFile
    # La clave de firma se genera localmente: nunca viaja en el paquete.
    $secretBytes = New-Object byte[] 32
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($secretBytes) } finally { $rng.Dispose() }
    $secret = -join ($secretBytes | ForEach-Object { $_.ToString("x2") })
    (Get-Content $envFile) -replace '^APP_SECRET_KEY=.*', "APP_SECRET_KEY=$secret" |
        Set-Content $envFile -Encoding UTF8
    Write-Ok "Se creo .env a partir de .env.example con una APP_SECRET_KEY nueva."
    Write-Warn "Revise DATABASE_URL en .env antes de continuar si su MySQL no es el de WAMP."
    return $true
}

function Get-MatrixBackendUrl {
    <# Lee host y puerto del .env; usa los valores por defecto si faltan. #>
    $envFile = Join-Path $script:MatrixRoot ".env"
    $hostName = "127.0.0.1"
    $port = "8000"
    if (Test-Path $envFile) {
        foreach ($line in Get-Content $envFile) {
            if ($line -match '^\s*APP_HOST\s*=\s*(.+)\s*$') { $hostName = $Matches[1].Trim() }
            if ($line -match '^\s*APP_PORT\s*=\s*(\d+)\s*$') { $port = $Matches[1].Trim() }
        }
    }
    if ($hostName -eq "0.0.0.0") { $hostName = "127.0.0.1" }
    return "http://${hostName}:${port}"
}

function Test-MatrixBackendUp {
    <# True si /health responde y la aplicacion se identifica como Matrix RH. #>
    param([int]$TimeoutSec = 3)
    try {
        $response = Invoke-RestMethod -Uri "$(Get-MatrixBackendUrl)/health" -TimeoutSec $TimeoutSec
        return ($response.app -eq "Matrix RH")
    }
    catch { return $false }
}

function Test-MatrixBackendReady {
    param([int]$TimeoutSec = 5)
    try {
        $response = Invoke-RestMethod -Uri "$(Get-MatrixBackendUrl)/ready" -TimeoutSec $TimeoutSec
        return [bool]$response.ready
    }
    catch { return $false }
}

function Test-OllamaModels {
    <# Nombre conservado por compatibilidad; prueba el adapter configurado. #>
    $code = Invoke-MatrixPython -Arguments @("-m", "scripts.preflight", "--llm-only")
    return ($code -eq 0)
}

function Find-WampMySql {
    <# Detecta una instalacion de WAMP para informar al operador. #>
    foreach ($path in @("C:\wamp64\www", "C:\wamp\www")) {
        if (Test-Path $path) { return $path }
    }
    return $null
}

function New-MatrixRuntimeDirs {
    foreach ($dir in @($script:LogDir, (Join-Path $script:MatrixRoot "var\uploads"), (Join-Path $script:MatrixRoot "var\qdrant"), (Join-Path $script:MatrixRoot "reports\tests"))) {
        if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
    }
}
