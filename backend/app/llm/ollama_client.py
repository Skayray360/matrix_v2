# Creado por Aldo Garcia.
"""Cliente unico hacia Ollama local.

Toda llamada a un modelo pasa por aqui: un solo punto para timeouts, reintentos,
keep-alive, metricas de latencia y preflight. Ningun otro modulo abre conexiones
HTTP hacia Ollama.

Reglas del proyecto que este cliente hace cumplir:

* los modelos y perfiles se resuelven desde la configuracion; la fachada
  ``ModelClient`` valida los endpoints y el requisito de ejecucion local;
* la dimension de embeddings se **comprueba en runtime**: si no coincide con la
  configurada se lanza ``EmbeddingDimensionMismatchError``. Jamas se trunca ni se
  rellena un vector;
* solo se reintentan errores transitorios (timeout / error de red / 5xx), nunca
  un 4xx, que indica una peticion incorrecta.
"""

from __future__ import annotations

import math
import time
from collections import OrderedDict
from dataclasses import dataclass
from hashlib import sha256
from threading import Lock
from typing import Any

import httpx

from app.common.errors import EmbeddingDimensionMismatchError, OllamaUnavailableError
from app.common.logging import get_logger
from app.config import get_settings

logger = get_logger(__name__)

MAX_TRANSIENT_RETRIES = 2
RETRY_BACKOFF_SECONDS = 0.75


@dataclass(frozen=True, slots=True)
class ChatResult:
    """Respuesta de generacion mas metricas para auditoria."""

    content: str
    model: str
    latency_ms: int
    prompt_eval_count: int | None = None
    eval_count: int | None = None
    total_duration_ns: int | None = None
    load_duration_ns: int | None = None
    prompt_eval_duration_ns: int | None = None
    eval_duration_ns: int | None = None
    prompt_eval_cached_count: int | None = None

    def performance_metrics(self) -> dict[str, int | float | None]:
        """Medidas del runtime, sin prompts. Ausente no equivale a cero ni a TTFT."""
        return {
            "prompt_eval_count": self.prompt_eval_count,
            "eval_count": self.eval_count,
            "prompt_eval_cached_count": self.prompt_eval_cached_count,
            "total_duration_ns": self.total_duration_ns,
            "load_duration_ns": self.load_duration_ns,
            "prompt_eval_duration_ns": self.prompt_eval_duration_ns,
            "eval_duration_ns": self.eval_duration_ns,
            "generation_tokens_per_second": (
                self.eval_count * 1_000_000_000 / self.eval_duration_ns
                if self.eval_count is not None and self.eval_duration_ns and self.eval_duration_ns > 0
                else None
            ),
        }


def _metric(data: dict[str, Any], name: str) -> int | None:
    value = data.get(name)
    return value if type(value) is int and value >= 0 else None


@dataclass(frozen=True, slots=True)
class ModelInventory:
    """Inventario de modelos disponibles en la instancia Ollama."""

    names: tuple[str, ...]
    digests: tuple[tuple[str, str], ...] = ()

    def has(self, model: str) -> bool:
        return model in self.names


class OllamaClient:
    """Cliente sincrono. FastAPI ejecuta las rutas de chat en threadpool."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        timeout: float | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.timeout = timeout if timeout is not None else settings.ollama_timeout_seconds
        self.keep_alive = settings.ollama_keep_alive
        self.embedding_model = settings.ollama_embedding_model
        self.expected_dimension = settings.ollama_embedding_dimension
        self.embedding_cache_size = settings.ollama_embedding_cache_size
        self._embedding_cache: OrderedDict[str, tuple[float, ...]] = OrderedDict()
        self._embedding_cache_lock = Lock()
        self._client = client or httpx.Client(
            trust_env=False,
            timeout=httpx.Timeout(self.timeout, connect=min(10.0, self.timeout)),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )

    # ------------------------------------------------------------------ HTTP
    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        """POST con reintentos limitados a errores transitorios."""
        url = f"{self.base_url}{path}"
        last_error: Exception | None = None

        for attempt in range(get_settings().llm_max_transient_retries + 1):
            try:
                response = self._client.post(url, json=payload)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = exc
                if attempt < get_settings().llm_max_transient_retries:
                    time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
                    continue
                break
            if response.status_code in (429, 503):
                raise OllamaUnavailableError("El servicio de IA esta ocupado.", detail=f"HTTP {response.status_code}")
            if response.status_code >= 500:
                last_error = OllamaUnavailableError(detail=f"HTTP {response.status_code}")
                if attempt < get_settings().llm_max_transient_retries:
                    time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
                    continue
                break
            if response.status_code >= 400:
                # 4xx no se reintenta: es un problema de la peticion (por ejemplo
                # modelo inexistente) y reintentar solo esconde el diagnostico.
                raise OllamaUnavailableError(
                    "La peticion al modelo local fue rechazada.",
                    detail=f"HTTP {response.status_code} en {path}",
                )
            return response.json()

        if isinstance(last_error, OllamaUnavailableError):
            detail = last_error.detail or last_error.message
        else:
            detail = str(last_error)
        raise OllamaUnavailableError("No fue posible contactar el servicio de IA local.", detail=detail)

    def _get(self, path: str) -> dict[str, Any]:
        try:
            response = self._client.get(f"{self.base_url}{path}", timeout=10.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise OllamaUnavailableError("No fue posible contactar el servicio de IA local.", detail=str(exc)) from exc

    # --------------------------------------------------------------- salud
    def ping(self) -> bool:
        try:
            response = self._client.get(f"{self.base_url}/api/tags", timeout=5.0)
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    def list_models(self) -> ModelInventory:
        data = self._get("/api/tags")
        names = tuple(str(m.get("name", "")) for m in data.get("models", []))
        return ModelInventory(
            names=names,
            digests=tuple((str(m.get("name", "")), str(m.get("digest", ""))) for m in data.get("models", [])),
        )

    # ----------------------------------------------------------- generacion
    def chat(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.1,
        num_ctx: int | None = None,
        max_tokens: int | None = None,
        stop: list[str] | None = None,
        response_schema: dict[str, Any] | None = None,
        think: bool | None = None,
        top_k: int | None = None,
    ) -> ChatResult:
        """Genera una respuesta con la API ``/api/chat``.

        La temperatura por defecto es baja a proposito: Matrix RH responde sobre
        politicas de RH y debe ceñirse a la evidencia, no producir variedad.
        """
        options: dict[str, Any] = {"temperature": temperature, "top_p": get_settings().llm_top_p}
        if num_ctx is not None:
            options["num_ctx"] = num_ctx
        if max_tokens is not None:
            options["num_predict"] = max_tokens
        if stop:
            options["stop"] = stop
        if top_k is not None:
            options["top_k"] = top_k

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "keep_alive": self.keep_alive,
            "options": options,
        }
        if response_schema is not None:
            payload["format"] = response_schema
        if think is not None:
            payload["think"] = think
        started = time.perf_counter()
        data = self._post("/api/chat", payload)
        latency_ms = int((time.perf_counter() - started) * 1000)

        message = data.get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            raise OllamaUnavailableError("Ollama devolvio una respuesta de chat no valida.")
        if data.get("done") is False or data.get("done_reason") not in (None, "stop"):
            raise OllamaUnavailableError("El modelo no completo la respuesta.")
        content = message["content"].strip()
        result = ChatResult(
            content=content,
            model=model,
            latency_ms=latency_ms,
            prompt_eval_count=_metric(data, "prompt_eval_count"),
            eval_count=_metric(data, "eval_count"),
            total_duration_ns=_metric(data, "total_duration"),
            load_duration_ns=_metric(data, "load_duration"),
            prompt_eval_duration_ns=_metric(data, "prompt_eval_duration"),
            eval_duration_ns=_metric(data, "eval_duration"),
            prompt_eval_cached_count=_metric(data, "prompt_eval_cached_count"),
        )
        logger.info(
            "llm.chat",
            extra={
                "selected_model": model,
                "latency_ms": latency_ms,
                "response_chars": len(content),
                **result.performance_metrics(),
            },
        )
        return result

    # ----------------------------------------------------------- embeddings
    def embed(self, texts: list[str], *, model: str | None = None) -> list[list[float]]:
        """Genera embeddings y **verifica la dimension real** de cada vector."""
        if not texts:
            return []
        target_model = model or self.embedding_model
        data = self._post(
            "/api/embed",
            {"model": target_model, "input": texts, "keep_alive": self.keep_alive, "truncate": False},
        )
        raw = data.get("embeddings")
        if not isinstance(raw, list) or len(raw) != len(texts):
            raise EmbeddingDimensionMismatchError(
                "La respuesta de embeddings no tiene la forma esperada.",
                detail=f"esperados={len(texts)} recibidos={len(raw) if isinstance(raw, list) else 'n/a'}",
            )
        vectors: list[list[float]] = []
        for vector in raw:
            if not isinstance(vector, list) or len(vector) != self.expected_dimension:
                actual = len(vector) if isinstance(vector, list) else "desconocida"
                raise EmbeddingDimensionMismatchError(
                    "La dimension de embeddings no coincide con la configurada.",
                    detail=(
                        f"modelo={target_model} esperada={self.expected_dimension} real={actual}. "
                        "No se trunca ni se rellena el vector."
                    ),
                )
            if any(isinstance(v, bool) or not isinstance(v, int | float) or not math.isfinite(v) for v in vector):
                raise EmbeddingDimensionMismatchError("El embedding contiene valores no numericos o no finitos.")
            vectors.append([float(v) for v in vector])
        return vectors

    def embed_one(self, text: str, *, model: str | None = None) -> list[float]:
        target_model = model or self.embedding_model
        if self.embedding_cache_size <= 0:
            return self.embed([text], model=target_model)[0]

        # La clave no conserva la pregunta del usuario: solo modelo + SHA-256.
        revision = self.embedding_revision() if hasattr(self, "embedding_revision") else "legacy"
        cache_key = f"{target_model}:{revision}:{sha256(text.encode('utf-8')).hexdigest()}"
        with self._embedding_cache_lock:
            cached = self._embedding_cache.get(cache_key)
            if cached is not None:
                self._embedding_cache.move_to_end(cache_key)
                return list(cached)

        vector = self.embed([text], model=target_model)[0]
        with self._embedding_cache_lock:
            self._embedding_cache[cache_key] = tuple(vector)
            self._embedding_cache.move_to_end(cache_key)
            while len(self._embedding_cache) > self.embedding_cache_size:
                self._embedding_cache.popitem(last=False)
        return vector

    def probe_embedding_dimension(self, *, model: str | None = None) -> int:
        """Devuelve la dimension real observada (preflight y diagnostico).

        No usa ``embed`` porque ese metodo ya exige que la dimension coincida; el
        preflight necesita poder **reportar** la discrepancia.
        """
        target_model = model or self.embedding_model
        data = self._post(
            "/api/embed",
            {
                "model": target_model,
                "input": ["matrix rh dimension probe"],
                "keep_alive": self.keep_alive,
                "truncate": False,
            },
        )
        vectors = data.get("embeddings") or []
        if not vectors or not isinstance(vectors[0], list):
            raise EmbeddingDimensionMismatchError(
                "El endpoint de embeddings no devolvio ningun vector.", detail=f"modelo={target_model}"
            )
        return len(vectors[0])

    def close(self) -> None:
        self._client.close()


_client: OllamaClient | None = None


def get_ollama_client() -> OllamaClient:
    global _client
    if _client is None:
        from app.llm.provider import ModelClient

        _client = ModelClient()
    return _client


def reset_ollama_client() -> None:
    global _client
    if _client is not None:
        _client.close()
    _client = None
