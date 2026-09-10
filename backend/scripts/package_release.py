# Creado por Aldo Garcia.
"""Empaquetado del ZIP final de entrega (seccion 39.6).

Incluye fuente, lockfiles, build del frontend, migraciones, seeds sinteticos,
documentos de prueba sinteticos, BAT/PowerShell, documentacion, pruebas y la
evidencia de auditoria permitida.

Excluye, de forma verificable: ``.env`` real, ``.venv``, ``node_modules``, caches,
logs con datos, tokens, API keys, certificados privados, bases reales y los
volumenes runtime de Qdrant.

Antes de escribir el ZIP se ejecuta el escaner de secretos sobre el contenido
seleccionado. Si aparece un secreto real, **no se genera el paquete**.

Uso:
    python -m scripts.package_release
    python -m scripts.package_release --output ../MatrixRH-1.2.1.zip
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path

from app import __version__
from app.config import PROJECT_ROOT

#: Directorios que nunca entran al paquete.
EXCLUDED_DIRS = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "htmlcov",
        "var",  # estado runtime: uploads, logs, volumen de Qdrant
        "playwright-report",
        "test-results",
        ".playwright",
        "matrix_rh_backend.egg-info",
        ".vscode",
        ".idea",
    }
)

#: Patrones de archivo excluidos. El `.env` real es el mas importante.
EXCLUDED_PATTERNS = (
    ".env",
    ".env.*",
    "*.pem",
    "*.pfx",
    "*.key",
    "*.p12",
    "*.crt",
    "*.log",
    "*.pyc",
    "*.sqlite3",
    "*.db",
    "*.bak",
    "Thumbs.db",
    ".DS_Store",
    # Cachés de herramientas: no son fuente y guardan rutas absolutas del equipo
    # donde se ejecutaron, que no tienen sentido en el equipo destino.
    ".coverage",
    ".coverage.*",
    "*.tsbuildinfo",
)

#: Excepciones a los patrones anteriores.
KEEP_PATTERNS = (".env.example",)

#: Evidencia narrativa que se requiere conservar. Tambien viajan todos los
#: Markdown historicos: su version/fecha permite interpretar cifras anteriores.
ALLOWED_REPORT_PATHS = frozenset(
    {
        "reports/README.md",
        "reports/RELEASE_VALIDATION_1.1.0.md",
        "reports/IMPLEMENTATION_V2_VALIDATION.md",
        "reports/FINAL_CONSOLIDATION_VALIDATION.md",
    }
)


@dataclass
class PackageStats:
    files: int = 0
    bytes_uncompressed: int = 0
    skipped_dirs: int = 0
    skipped_files: int = 0


def _is_excluded_file(path: Path) -> bool:
    name = path.name
    if any(fnmatch.fnmatch(name, keep) for keep in KEEP_PATTERNS):
        return False
    return any(fnmatch.fnmatch(name, pattern) for pattern in EXCLUDED_PATTERNS)


def iter_package_files(root: Path) -> list[Path]:
    """Selecciona los archivos que entran al paquete."""
    seleccionados: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        partes = path.relative_to(root).parts
        if any(parte in EXCLUDED_DIRS or parte.startswith(".venv.previous-") for parte in partes):
            continue
        if _is_excluded_file(path):
            continue
        # Se preserva toda la documentacion historica Markdown. La evidencia
        # automatica JSON/XML puede contener rutas o datos runtime y no viaja.
        relative_name = path.relative_to(root).as_posix()
        if (
            partes and partes[0] == "reports"
            and relative_name not in ALLOWED_REPORT_PATHS and path.suffix.lower() != ".md"
        ):
            continue
        seleccionados.append(path)
    return seleccionados


def verify_no_secrets(files: list[Path], root: Path) -> list[str]:
    """Ejecuta el escaner de secretos sobre el contenido seleccionado."""
    from scripts.secrets_scan import scan

    relativas = {p.relative_to(root).as_posix() for p in files}
    hallazgos = scan(root)
    return [
        f"{f.file}:{f.line} [{f.rule}]"
        for f in hallazgos
        if f.classification == "real" and f.file in relativas
    ]


def build_zip(root: Path, destino: Path, files: list[Path]) -> PackageStats:
    stats = PackageStats()
    destino.parent.mkdir(parents=True, exist_ok=True)
    raiz_interna = f"matrix-rh-{__version__}"
    checksums: list[str] = []

    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archivo:
        for path in files:
            relativa = path.relative_to(root)
            if relativa.as_posix() == "SHA256SUMS.txt":
                continue  # Se regenera al empaquetar una carpeta previamente extraida.
            contenido = path.read_bytes()
            info = zipfile.ZipInfo.from_file(path, arcname=f"{raiz_interna}/{relativa.as_posix()}")
            archivo.writestr(info, contenido, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
            checksums.append(f"{hashlib.sha256(contenido).hexdigest()}  {relativa.as_posix()}")
            stats.files += 1
            stats.bytes_uncompressed += len(contenido)
        manifiesto = ("\n".join(checksums) + "\n").encode("utf-8")
        archivo.writestr(f"{raiz_interna}/SHA256SUMS.txt", manifiesto)
        stats.files += 1
        stats.bytes_uncompressed += len(manifiesto)
    return stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Empaqueta el ZIP de entrega de Matrix RH")
    parser.add_argument("--output", default="", help="ruta del ZIP (por defecto, junto al proyecto)")
    parser.add_argument(
        "--skip-secret-scan",
        action="store_true",
        help="omite la verificacion de secretos (NO recomendado)",
    )
    args = parser.parse_args(argv)

    root = PROJECT_ROOT
    destino = Path(args.output) if args.output else root.parent / f"MatrixRH-{__version__}.zip"

    print(f"Proyecto: {root}")
    files = [path for path in iter_package_files(root) if path.resolve() != destino.resolve()]
    print(f"Archivos seleccionados: {len(files)}")

    if not args.skip_secret_scan:
        print("Verificando que no viaje ningun secreto real...")
        problemas = verify_no_secrets(files, root)
        if problemas:
            print("SE ABORTA EL EMPAQUETADO: hay secretos reales en el contenido seleccionado.")
            for problema in problemas:
                print(f"  - {problema}")
            return 1
        print("  0 secretos reales.")

    # Comprobaciones de contenido obligatorio.
    relativas = {p.relative_to(root).as_posix() for p in files}
    obligatorios = (
        "README.md",
        "SECURITY.md",
        "CHANGELOG.md",
        ".htaccess",
        ".env.example",
        "docker-compose.yml",
        "INSTALAR_MATRIX_RH.bat",
        "install.bat",
        "INICIAR_MATRIX_RH.bat",
        "DETENER_MATRIX_RH.bat",
        "DIAGNOSTICO_MATRIX_RH.bat",
        "backend/pyproject.toml",
        "backend/Dockerfile",
        "frontend/package.json",
        # Lockfile canonico (npm): sin el, la instalacion en destino no es
        # reproducible. Se exige para no publicar un ZIP sin lockfile.
        "frontend/package-lock.json",
        "frontend/dist/index.html",
        "backend/uv.lock",
        "docs/FINAL_AUDIT.md",
        "docs/EXTERNAL_DEPENDENCIES_STATUS.md",
        "reports/RELEASE_VALIDATION_1.1.0.md",
        "reports/IMPLEMENTATION_V2_VALIDATION.md",
        "reports/FINAL_CONSOLIDATION_VALIDATION.md",
        "docs/FINAL_CONSOLIDATION.md",
    )
    faltantes = [nombre for nombre in obligatorios if nombre not in relativas]
    if faltantes:
        print("SE ABORTA EL EMPAQUETADO: faltan archivos obligatorios en la raiz.")
        for nombre in faltantes:
            print(f"  - {nombre}")
        return 1

    prohibidos = [r for r in relativas if r == ".env" or r.startswith("var/") or "/node_modules/" in r]
    if prohibidos:
        print("SE ABORTA EL EMPAQUETADO: contenido prohibido seleccionado.")
        for nombre in prohibidos[:10]:
            print(f"  - {nombre}")
        return 1

    # El gestor del frontend (npm) debe fijarse con hash de integridad para que
    # corepack verifique criptograficamente el binario que descarga. Sin el hash,
    # la provision del gestor solo confia en TLS y el registro: no debe publicarse
    # un release asi. Bloqueante a proposito (en desarrollo es solo un aviso).
    from scripts.verify_supply_chain import package_manager_pin

    pm, con_hash = package_manager_pin(root / "frontend")
    if not con_hash:
        print("SE ABORTA EL EMPAQUETADO: el gestor del frontend no fija hash de integridad.")
        print(f"  packageManager actual: {pm or '(ausente)'}")
        print("  Fije 'npm@<version>+sha512.<hash>' en frontend/package.json.")
        print("  Obtenga el hash oficial verificado y ejecute el gestor mediante corepack npm.")
        return 1

    # El frontend compilado es obligatorio arriba; -SkipFrontend permite
    # reutilizarlo en destino cuando no se instala Node/Corepack.

    stats = build_zip(root, destino, files)
    tamano = destino.stat().st_size

    print("")
    print(f"ZIP generado: {destino}")
    print(f"  archivos: {stats.files}")
    print(f"  tamano comprimido: {tamano / (1024 * 1024):.2f} MB")
    print(f"  tamano sin comprimir: {stats.bytes_uncompressed / (1024 * 1024):.2f} MB")
    print("")
    print("Prepare los prerrequisitos y la configuracion indicados en README.md.")
    print("Despues extraiga el paquete y ejecute install.bat para instalar e iniciar.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
