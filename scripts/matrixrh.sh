#!/usr/bin/env bash
# Creado por Aldo Garcia.
# ---------------------------------------------------------------------------
# Equivalente shell de los .bat de la raiz para entornos no-Windows.
# No duplica logica: delega en los mismos modulos Python del backend.
# ---------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_PY="${ROOT}/.venv/bin/python"
BACKEND="${ROOT}/backend"
PID_FILE="${ROOT}/var/matrixrh-backend.pid"
LOG_DIR="${ROOT}/var/logs"

info()  { printf '  \033[0;90m-> %s\033[0m\n' "$1"; }
ok()    { printf '  \033[0;32m[ OK ]\033[0m %s\n' "$1"; }
warn()  { printf '  \033[0;33m[WARN]\033[0m %s\n' "$1"; }
fail()  { printf '  \033[0;31m[FAIL]\033[0m %s\n' "$1"; }
section() { printf '\n\033[0;36m=== %s ===\033[0m\n' "$1"; }

require_python312() {
    if ! command -v python3.12 >/dev/null 2>&1; then
        fail "Se requiere Python 3.12. Instalelo y vuelva a ejecutar."
        exit 1
    fi
    ok "Python 3.12 disponible"
}

py() {
    # Ejecuta un modulo del backend con el PYTHONPATH correcto.
    ( cd "${BACKEND}" && PYTHONPATH="${BACKEND}" "${VENV_PY}" "$@" )
}

backend_url() {
    py -c 'from app.config import get_settings; s=get_settings(); host="127.0.0.1" if s.app_host=="0.0.0.0" else s.app_host; print(f"http://{host}:{s.app_port}")'
}

process_owned() {
    # No basta con un PID: puede haberse reutilizado despues de un reinicio.
    "${VENV_PY}" - "${ROOT}" "$1" <<'PY_CHECK'
import os
import sys
from pathlib import Path
import psutil
try:
    root = Path(sys.argv[1]).resolve()
    process = psutil.Process(int(sys.argv[2]))
    args = process.cmdline()
    expected = root / '.venv/bin/python'
    owned = (len(args) >= 4 and Path(args[0]).absolute() == expected
             and args[1:4] == ['-m', 'scripts.bootstrap', 'serve']
             and Path(process.cwd()).resolve() == root / 'backend'
             and Path(process.exe()).resolve() == expected.resolve())
except (OSError, ValueError, psutil.Error):
    owned = False
sys.exit(0 if owned else 1)
PY_CHECK
}

backend_state() {
    "${VENV_PY}" - "$1" "$2" <<'PY_CHECK'
import json
import sys
import urllib.request
try:
    with urllib.request.urlopen(sys.argv[1] + sys.argv[2], timeout=3) as response:
        data = json.load(response)
    valid = data.get('app') == 'Matrix RH' if sys.argv[2] == '/health' else data.get('ready') is True
except Exception:
    valid = False
sys.exit(0 if valid else 1)
PY_CHECK
}

cmd_install() {
    section "MATRIX RH - INSTALACION"
    require_python312

    # uv es obligatorio, igual que en el instalador de Windows: garantiza una
    # instalacion REPRODUCIBLE desde uv.lock (no resuelve rangos ni trae una
    # version publicada hace minutos).
    if ! command -v uv >/dev/null 2>&1; then
        fail "Se requiere uv para una instalacion reproducible desde uv.lock."
        fail "Instalelo por un canal autorizado y vuelva a ejecutar."
        exit 1
    fi

    if [ ! -f "${ROOT}/.env" ]; then
        cp "${ROOT}/.env.example" "${ROOT}/.env"
        # La clave de firma se genera localmente; nunca viaja en el paquete.
        local secret
        secret="$(python3.12 -c 'import secrets; print(secrets.token_hex(32))')"
        sed -i.bak "s|^APP_SECRET_KEY=.*|APP_SECRET_KEY=${secret}|" "${ROOT}/.env"
        rm -f "${ROOT}/.env.bak"
        ok "Se creo .env con una APP_SECRET_KEY nueva"
    else
        ok ".env ya existe (no se sobrescribe)"
    fi

    mkdir -p "${LOG_DIR}" "${ROOT}/var/uploads" "${ROOT}/var/qdrant" \
        "${ROOT}/reports/tests" "${ROOT}/reports/security"

    info "Sincronizando el backend desde uv.lock (--frozen)..."
    ( cd "${BACKEND}" && UV_PROJECT_ENVIRONMENT="${ROOT}/.venv" uv sync --frozen --no-dev --python python3.12 --no-python-downloads )
    ok "Dependencias del backend sincronizadas exactamente desde uv.lock"

    if ! command -v node >/dev/null 2>&1 || ! command -v corepack >/dev/null 2>&1; then
        fail "Se requieren Node 22.12+ y Corepack para compilar la interfaz."
        exit 1
    fi
    node -e 'const [major,minor]=process.versions.node.split(".").map(Number); if(major<22 || (major===22 && minor<12)) process.exit(1)' || {
        fail "La version de Node no cumple 22.12+."; exit 1;
    }
    export COREPACK_ENABLE_DOWNLOAD_PROMPT=0
    info "Instalando el frontend mediante el gestor con hash y package-lock.json..."
    py -m scripts.verify_supply_chain --lock-only || { fail "Lockfile bloqueado; no se descargan paquetes."; exit 1; }
    ( cd "${ROOT}/frontend" && corepack npm audit --audit-level=low --include=dev --include=optional --include=peer ) || {
        fail "npm audit encontro avisos o no pudo verificarlos; no se descargan paquetes."; exit 1;
    }
    ( cd "${ROOT}/frontend" && corepack npm ci --ignore-scripts --no-audit --no-fund --include=dev --include=optional --include=peer )
    py -m scripts.verify_supply_chain || { fail "Fallo la cadena de suministro; no se compila."; exit 1; }
    ( cd "${ROOT}/frontend" && corepack npm run build )
    ok "Frontend compilado sin ejecutar scripts de instalacion"

    py -m scripts.bootstrap setup
    py -m scripts.preflight
}

cmd_start() {
    section "MATRIX RH - ARRANQUE"
    local url; url="$(backend_url)"

    if backend_state "${url}" /health; then
        if [ -f "${PID_FILE}" ] && process_owned "$(cat "${PID_FILE}")" && backend_state "${url}" /ready \
            && [ -f "${ROOT}/frontend/dist/index.html" ]; then
            ok "Matrix RH ya esta listo en ${url}"
            return 0
        fi
        fail "El puerto responde pero no es un proceso propio listo, o falta la interfaz."
        exit 1
    fi

    [ -f "${ROOT}/frontend/dist/index.html" ] || { fail "Falta frontend/dist; ejecute install."; exit 1; }
    py -m scripts.preflight || { fail "El preflight fallo: no se arranca"; exit 1; }

    mkdir -p "${LOG_DIR}"
    local stamp; stamp="$(date +%Y%m%d-%H%M%S)"
    (
        cd "${BACKEND}"
        PYTHONPATH="${BACKEND}" nohup "${VENV_PY}" -m scripts.bootstrap serve --skip-preflight \
            >"${LOG_DIR}/backend-${stamp}.log" 2>"${LOG_DIR}/backend-${stamp}.err.log" &
        echo $! > "${PID_FILE}"
    )
    local backend_pid; backend_pid="$(cat "${PID_FILE}")"
    info "PID ${backend_pid}  logs en ${LOG_DIR}"

    local waited=0
    while [ "${waited}" -lt 180 ]; do
        if ! kill -0 "${backend_pid}" 2>/dev/null; then break; fi
        if backend_state "${url}" /health && backend_state "${url}" /ready; then
            ok "Backend e interfaz listos en ${url}"
            return 0
        fi
        sleep 2; waited=$((waited + 2))
    done
    fail "El backend no alcanzo /health y /ready en 180 s"
    if process_owned "${backend_pid}"; then kill "${backend_pid}"; fi
    rm -f "${PID_FILE}"
    tail -n 20 "${LOG_DIR}/backend-${stamp}.err.log" || true
    exit 1
}

cmd_stop() {
    section "MATRIX RH - DETENER"
    if [ -f "${PID_FILE}" ]; then
        local backend_pid; backend_pid="$(cat "${PID_FILE}")"
        if process_owned "${backend_pid}"; then
            kill "${backend_pid}"; ok "Detenido PID ${backend_pid}"
        else
            warn "PID ausente o ajeno: no se detiene ningun proceso."
        fi
        rm -f "${PID_FILE}"
    else
        ok "Matrix RH no estaba en ejecucion"
    fi
}

cmd_diagnose() {
    section "MATRIX RH - DIAGNOSTICO"
    py -m scripts.preflight --read-only
}

cmd_validate() {
    section "MATRIX RH - VALIDACION"
    cmd_stop
    py -m scripts.bootstrap migrate
    py -m scripts.bootstrap seed
    py -m scripts.bootstrap ingest
    py -m pytest tests/unit tests/integration tests/security -q
    py -m scripts.rag_eval --retrieval --output "${ROOT}/reports/tests/rag_eval.json"
    py -m scripts.secrets_scan --allow-env --output "${ROOT}/reports/security/secrets_scan.json"
    ok "Validacion completada"
}

usage() {
    cat <<'EOF'
Uso: ./scripts/matrixrh.sh <comando>

  install    Instalacion idempotente completa
  start      Arranca el backend (preflight + espera a /health y /ready)
  stop       Detiene el backend
  diagnose   Diagnostico de solo lectura
  validate   Migraciones, seed, ingesta, pruebas, RAG y secretos

En Windows use los .bat de la raiz.
EOF
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
case "${1:-}" in
    install)  cmd_install; cmd_start ;;
    start)    cmd_start ;;
    stop)     cmd_stop ;;
    diagnose) cmd_diagnose ;;
    validate) cmd_validate ;;
    *)        usage; exit 1 ;;
esac
fi
