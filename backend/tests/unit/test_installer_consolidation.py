# Creado por Aldo Garcia.
"""Regresiones de instalacion; no conecta ni modifica servicios corporativos."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import package_release, preflight, verify_supply_chain

ROOT = Path(__file__).resolve().parents[3]
pytestmark = pytest.mark.unit


def test_paquete_preserva_documentacion_historica_y_excluye_runtime(tmp_path: Path):
    for name in (
        "README.md", "reports/historico/REVISION.md", "reports/tests/resultados.json",
        "var/uploads/privado.txt", ".env", "frontend/dist/index.html", "source-history.bundle",
        ".venv.previous-20260910/lib/cache.dat",
    ):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("sintetico", encoding="utf-8")
    external = tmp_path.parent / "externo.txt"
    external.write_text("sintetico", encoding="utf-8")
    (tmp_path / "link.txt").symlink_to(external)
    selected = {p.relative_to(tmp_path).as_posix() for p in package_release.iter_package_files(tmp_path)}
    assert selected == {
        "README.md", "reports/historico/REVISION.md", "frontend/dist/index.html", "source-history.bundle",
    }


def test_lockfile_debe_corresponder_al_gestor_fijado(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(verify_supply_chain, "FRONTEND", tmp_path)
    (tmp_path / "package.json").write_text(json.dumps({"packageManager": "npm@10.9.0+sha512." + "a" * 128}))
    (tmp_path / ".npmrc").write_text("ignore-scripts=true\n")
    (tmp_path / "pnpm-lock.yaml").write_text("lockfileVersion: 9\n")
    report = verify_supply_chain.Report()
    verify_supply_chain.check_reproducible_install(report)
    assert not report.ok
    (tmp_path / "package-lock.json").write_text('{"lockfileVersion":3}')
    report = verify_supply_chain.Report()
    verify_supply_chain.check_reproducible_install(report)
    assert report.ok


@pytest.mark.parametrize("pin", ["npm@10.9.0+sha512.abc123", "npm@10.9.0+sha0.abc", "npm@10.9.0"])
def test_hash_de_gestor_incompleto_no_satisface_gate(tmp_path: Path, pin: str):
    (tmp_path / "package.json").write_text(json.dumps({"packageManager": pin}))
    assert verify_supply_chain.package_manager_pin(tmp_path) == (pin, False)


def test_preflight_read_only_no_abre_qdrant_embebido(tmp_path: Path, monkeypatch):
    from app.config import QdrantMode
    from app.rag import vector_store

    def forbidden():
        pytest.fail("Un diagnostico de solo lectura no debe adquirir el lock ni crear archivos")

    monkeypatch.setattr(vector_store, "get_vector_store", forbidden)
    settings = SimpleNamespace(qdrant_mode=QdrantMode.EMBEDDED, qdrant_storage_path=tmp_path / "ausente")
    report = preflight.PreflightReport()
    preflight.check_qdrant(report, settings, read_only=True)
    assert report.ok
    assert report.checks[0].status == preflight.WARN
    assert not settings.qdrant_storage_path.exists()


def test_preflight_usa_adapter_configurado_y_cierra_cliente(monkeypatch):
    from app.llm import provider
    from app.llm.ollama_client import ModelInventory

    closed = []

    class FakeClient:
        def list_models(self):
            return ModelInventory(names=("modelo-local-a", "modelo-local-b", "embed-local"))

        def probe_embedding_dimension(self):
            return 1024

        def close(self):
            closed.append(True)

    monkeypatch.setattr(provider, "ModelClient", FakeClient)
    settings = SimpleNamespace(
        llm_provider="openai_compatible", llm_deep_provider="openai_compatible",
        llm_embedding_provider="openai_compatible", ollama_fast_model="modelo-local-a",
        ollama_deep_model="modelo-local-b", ollama_embedding_model="embed-local",
        ollama_embedding_dimension=1024,
    )
    report = preflight.PreflightReport()
    preflight.check_ollama(report, settings)
    assert report.ok
    assert closed == [True]
    assert {c.name for c in report.checks} >= {"modelo_fast", "modelo_deep", "modelo_embedding"}
    assert any("1024" in c.detail for c in report.checks)


def test_uv_distribuciones_sin_target_conservan_version_exacta():
    content = (ROOT / "windows/Install-MatrixRH.ps1").read_text()
    pattern = re.search(r"\$uvVersionPattern = '([^']+)'", content).group(1)
    assert re.fullmatch(pattern, "uv 0.12.8")
    assert re.fullmatch(pattern, "uv 0.12.8 (fece32fc5 2026-07-28)")
    assert not re.fullmatch(pattern, "uv 0.12.9")


def test_helper_mysql_windows_es_python_valido_y_no_expone_credenciales_en_argv():
    content = (ROOT / "windows/Common-MatrixRH.ps1").read_text()
    source = content.split('$codigo = @"\n', 1)[1].split('\n"@', 1)[0]
    compile(source, "dbcheck-sintetico.py", "exec")
    assert "sys.argv[2]" not in source
    assert "inspect_ownership(engine)" in source
    assert "SHOW DATABASES LIKE" not in source


@pytest.mark.skipif(sys.platform == "win32", reason="Contrato Bash ejecutado en Linux; Windows tiene job de PowerShell")
def test_detencion_shell_distingue_un_proceso_de_otra_carpeta(tmp_path: Path):
    backend = tmp_path / "backend"
    scripts = backend / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "__init__.py").write_text("")
    (scripts / "bootstrap.py").write_text("import sys\nsys.stdin.read()\n")
    python_link = tmp_path / ".venv/bin/python"
    python_link.parent.mkdir(parents=True)
    python_link.symlink_to(sys.executable)
    process = subprocess.Popen(
        [str(python_link), "-m", "scripts.bootstrap", "serve"], cwd=backend, stdin=subprocess.PIPE,
    )
    try:
        import psutil

        try:
            psutil.Process(process.pid).cwd()
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            assert process.poll() is None
            pytest.skip("El sandbox no expone /proc del hijo vivo; el control real falla cerrado")
        command = [
            "bash", "-c", 'source "$1"; ROOT="$2"; VENV_PY="$3"; process_owned "$4"',
            "matrix-contract", str(ROOT / "scripts/matrixrh.sh"), str(tmp_path), sys.executable,
        ]
        assert subprocess.run([*command, str(process.pid)], check=False, timeout=10).returncode == 0
        assert subprocess.run([*command, str(__import__("os").getpid())], check=False, timeout=10).returncode == 1
    finally:
        process.communicate(timeout=5)
