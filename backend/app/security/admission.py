# Creado por Aldo Garcia.
"""Admision acotada por proceso; no mantiene una cola ilimitada ni reserva SQL."""

from contextlib import contextmanager
from threading import Lock

from app.common.errors import OllamaUnavailableError

_lock = Lock()
_active: dict[str, int] = {}


@contextmanager
def admission(key: str, limit: int):
    with _lock:
        if _active.get(key, 0) >= limit:
            raise OllamaUnavailableError("Capacidad ocupada. Intente de nuevo mas tarde.", detail="admission_full")
        _active[key] = _active.get(key, 0) + 1
    try:
        yield
    finally:
        with _lock:
            _active[key] -= 1
            if _active[key] == 0:
                del _active[key]


def snapshot() -> dict[str, int]:
    with _lock:
        return dict(_active)
