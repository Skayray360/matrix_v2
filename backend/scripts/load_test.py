# Creado por Aldo Garcia.
"""Carga local con sesiones de prueba distintas; no crea usuarios ni guarda tokens."""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import time
from collections import Counter
from pathlib import Path

import httpx


def percentile(values: list[float], q: float) -> float | None:
    return sorted(values)[max(0, math.ceil(len(values) * q) - 1)] if values else None


async def run(args) -> dict:
    import uuid

    sessions = json.loads(args.sessions.read_text(encoding="utf-8"))
    prompts = json.loads(args.prompts.read_text(encoding="utf-8"))
    if len(sessions) < args.users or not prompts or not all(isinstance(p, str) and p.strip() for p in prompts):
        raise ValueError("Se requieren sesiones suficientes y prompts documentales no vacios.")
    clients = [
        httpx.AsyncClient(
            base_url=args.base_url,
            trust_env=False,
            timeout=args.timeout,
            cookies={args.cookie_name: entry["session_token"]},
            headers={"X-CSRF-Token": entry["csrf_token"]},
        )
        for entry in sessions[: args.users]
    ]
    latencies, all_latencies, statuses = [], [], Counter()
    grounded, citations, completed = 0, 0, 0
    try:
        # Preparacion fuera del reloj de carga: comprobar usuarios distintos.
        identities = set()
        for client in clients:
            profile = await client.get("/api/v1/me")
            profile.raise_for_status()
            identities.add(profile.json()["user_id"])
        if len(identities) != args.users:
            raise ValueError("Cada usuario concurrente debe tener una identidad de prueba distinta.")
        started = time.monotonic()

        async def worker(index: int):
            nonlocal grounded, citations, completed
            conversation = None
            turn = 0
            while time.monotonic() - started < args.duration:
                before = time.monotonic()
                try:
                    response = await clients[index].post(
                        "/api/v1/chat",
                        json={
                            "conversation_id": conversation,
                            "message": prompts[(index + turn) % len(prompts)],
                            "client_request_id": str(uuid.uuid4()),
                        },
                    )
                    elapsed = time.monotonic() - before
                    if response.is_success:
                        data = response.json()
                        if not isinstance(data, dict) or any(
                            not isinstance(data.get(key), str) or not data[key].strip()
                            for key in ("conversation_id", "message_id", "answer")
                        ):
                            raise ValueError("Respuesta de chat incompleta")
                        conversation = data["conversation_id"]
                        latencies.append(elapsed)
                        grounded += bool(data.get("grounded"))
                        citations += bool(data.get("sources"))
                        completed += 1
                    statuses[str(response.status_code)] += 1
                    if response.status_code in (429, 503):
                        # Un encabezado incorrecto no convierte un rechazo en
                        # dos intentos ni permite una espera indefinida.
                        try:
                            delay = float(response.headers.get("Retry-After", "1"))
                            if not math.isfinite(delay):
                                delay = 1
                        except ValueError:
                            delay = 1
                        await asyncio.sleep(max(0, min(delay, 5)))
                except (httpx.HTTPError, ValueError, KeyError):
                    elapsed = time.monotonic() - before
                    statuses["transport_or_contract_error"] += 1
                all_latencies.append(elapsed)
                turn += 1

        await asyncio.gather(*(worker(i) for i in range(args.users)))
        total = sum(statuses.values())
        error_pct = 100 * (total - completed) / total if total else 100
        p95 = percentile(latencies, 0.95)
        # Sin umbrales proporcionados por TI no se inventa una aprobacion.
        accepted = None
        if args.slo_p95 is not None and args.max_error_pct is not None:
            accepted = bool(p95 is not None and p95 <= args.slo_p95 and error_pct <= args.max_error_pct)
        return {
            "users": args.users,
            "requested_duration_s": args.duration,
            "actual_duration_s": round(time.monotonic() - started, 3),
            "requests": total,
            "completed": completed,
            "statuses": dict(statuses),
            "error_pct": error_pct,
            "success_p50_s": percentile(latencies, 0.50),
            "success_p95_s": p95,
            "success_p99_s": percentile(latencies, 0.99),
            "all_p95_s": percentile(all_latencies, 0.95),
            "grounded_responses": grounded,
            "responses_with_citations": citations,
            "slo_p95_s": args.slo_p95,
            "max_error_pct": args.max_error_pct,
            "latency_error_gate_passed": accepted,
            "capacity_certified": False,
            "note": "No mide TTFT ni verifica contenido. Requiere hardware, calidad y recuperacion correlacionados.",
        }
    finally:
        await asyncio.gather(*(client.aclose() for client in clients))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--prompts", type=Path, required=True)
    parser.add_argument("--users", type=int, choices=range(1, 251), required=True)
    parser.add_argument("--duration", type=float, default=300)
    parser.add_argument("--timeout", type=float, default=150)
    parser.add_argument("--cookie-name", default="matrixrh_session")
    parser.add_argument("--slo-p95", type=float)
    parser.add_argument("--max-error-pct", type=float)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.duration <= 0 or args.timeout <= 0:
        parser.error("duration y timeout deben ser positivos")
    result = asyncio.run(run(args))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 1 if result["latency_error_gate_passed"] is False else 0


if __name__ == "__main__":
    raise SystemExit(main())
