# Creado por Aldo Garcia.
"""El gate no aprueba pasos obligatorios omitidos ni usa evidencia obsoleta."""

import json
from types import SimpleNamespace

import pytest

from scripts import run_quality_gate as gate


@pytest.mark.parametrize(
    ("status", "blocking", "expected", "code"),
    [
        (gate.SKIPPED, True, gate.INCOMPLETE, 2),
        (gate.INCOMPLETE, True, gate.INCOMPLETE, 2),
        (gate.FAIL, True, gate.FAIL, 1),
        (gate.SKIPPED, False, gate.PASS, 0),
        (gate.PASS, True, gate.PASS, 0),
    ],
)
def test_verdict_distinguishes_missing_required_evidence(tmp_path, monkeypatch, status, blocking, expected, code):
    monkeypatch.setattr(gate, "build_gates", lambda _args: [gate.GateResult("synthetic", status, blocking=blocking)])
    output = tmp_path / "result.json"
    assert gate.main(["--output", str(output)]) == code
    assert json.loads(output.read_text())["overall"] == expected


@pytest.mark.parametrize(("count", "skipped", "expected"), [(10, 2, gate.INCOMPLETE), (0, 0, gate.INCOMPLETE), (10, 0, gate.PASS)])
def test_junit_zero_exit_does_not_hide_skipped_cases(tmp_path, monkeypatch, count, skipped, expected):
    report = tmp_path / "junit.xml"

    def run(*_args, **_kwargs):
        report.write_text(f'<testsuites><testsuite tests="{count}" skipped="{skipped}"/></testsuites>')
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(gate.subprocess, "run", run)
    result = gate._run(["synthetic"], cwd=tmp_path, name="integration", require_complete_junit=report)
    assert result.status == expected


def test_never_accepts_a_previous_junit_report(tmp_path, monkeypatch):
    report = tmp_path / "junit.xml"
    report.write_text('<testsuites><testsuite tests="10" skipped="0"/></testsuites>')
    monkeypatch.setattr(gate.subprocess, "run", lambda *_args, **_kwargs: SimpleNamespace(returncode=0))
    result = gate._run(["synthetic"], cwd=tmp_path, name="integration", require_complete_junit=report)
    assert result.status == gate.FAIL


def test_failure_takes_precedence_over_incomplete(tmp_path, monkeypatch):
    monkeypatch.setattr(gate, "build_gates", lambda _args: [
        gate.GateResult("missing", gate.SKIPPED), gate.GateResult("broken", gate.FAIL),
    ])
    assert gate.main(["--output", str(tmp_path / "result.json")]) == 1
