# Creado por Aldo Garcia.
"""Cada intento debe producir un solo resultado, incluso con un HTTP 200 invalido."""

import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest

from scripts import load_test

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("body,expected", [
    ("not-json", "transport_or_contract_error"),
    ({"conversation_id": "c"}, "transport_or_contract_error"),
    ({"conversation_id": "c", "message_id": "m", "answer": "   "}, "transport_or_contract_error"),
    ({"conversation_id": "c", "message_id": "m", "answer": "Texto sintetico", "sources": []}, "200"),
])
def test_one_attempt_one_outcome(tmp_path, monkeypatch, body, expected):
    sessions = tmp_path / "sessions.json"
    sessions.write_text(json.dumps([{"session_token": "synthetic", "csrf_token": "synthetic"}]))
    prompts = tmp_path / "prompts.json"
    prompts.write_text(json.dumps(["Pregunta documental sintetica"]))
    clock = [0.0]
    monkeypatch.setattr(load_test.time, "monotonic", lambda: clock[0])
    actual_client = httpx.AsyncClient

    def respond(request):
        if request.method == "GET":
            return httpx.Response(200, json={"user_id": "synthetic-user"})
        clock[0] += 2
        return httpx.Response(200, json=body) if isinstance(body, dict) else httpx.Response(200, text=body)

    monkeypatch.setattr(
        load_test.httpx, "AsyncClient",
        lambda **kwargs: actual_client(transport=httpx.MockTransport(respond), **kwargs),
    )
    args = SimpleNamespace(sessions=sessions, prompts=prompts, users=1, base_url="http://127.0.0.1:8000",
                           timeout=3, cookie_name="synthetic", duration=1, slo_p95=3, max_error_pct=0)
    result = asyncio.run(load_test.run(args))
    assert result["requests"] == 1
    assert result["statuses"] == {expected: 1}
    assert result["completed"] == (1 if expected == "200" else 0)
    assert result["latency_error_gate_passed"] is (expected == "200")
    assert result["capacity_certified"] is False
