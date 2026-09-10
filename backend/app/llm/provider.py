# Creado por Aldo Garcia.
"""Contrato de inferencia y adapters HTTP. El negocio no construye payloads de proveedor."""

from __future__ import annotations

import json
import math
import re
import time
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Literal, Protocol
from urllib.parse import quote, urlparse

import httpx
from jsonschema import Draft202012Validator

from app.common.errors import ConfigurationError, EmbeddingDimensionMismatchError, OllamaUnavailableError
from app.config import get_settings
from app.llm.ollama_client import ChatResult, ModelInventory, OllamaClient, _metric
from app.security.admission import admission

_deadline: ContextVar[float | None] = ContextVar("matrix_inference_deadline", default=None)


@contextmanager
def inference_deadline():
    token = _deadline.set(time.monotonic() + get_settings().llm_request_deadline_seconds)
    try:
        yield
    finally:
        _deadline.reset(token)


class InferenceClient(Protocol):
    def chat(self, *, model: str, messages: list[dict[str, str]], **kwargs: Any) -> ChatResult: ...
    def embed(self, texts: list[str], *, model: str | None = None) -> list[list[float]]: ...
    def embed_one(self, text: str, *, model: str | None = None) -> list[float]: ...


def vertex_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Subset explicito de responseSchema. No se eliminan restricciones en silencio.

    La validacion completa de JSON Schema ocurre otra vez al recibir la respuesta.
    """
    definitions = schema.get("$defs", {})

    def convert(node: dict[str, Any], depth: int = 0) -> dict[str, Any]:
        if depth > 24:
            raise ConfigurationError("El schema es recursivo o demasiado profundo.")
        if "$ref" in node:
            ref = node["$ref"]
            if not ref.startswith("#/$defs/") or ref[8:] not in definitions:
                raise ConfigurationError("Solo se admiten referencias locales en el schema.")
            return convert(definitions[ref[8:]], depth + 1)
        out: dict[str, Any] = {}
        for key, value in node.items():
            if key in ("$defs", "title", "default", "additionalProperties"):
                # Vertex no soporta estos campos; jsonschema los exige en la salida.
                continue
            if key == "type":
                if value == "null":
                    out["nullable"] = True
                else:
                    out[key] = value.upper()
            elif key == "properties":
                out[key] = {name: convert(child, depth + 1) for name, child in value.items()}
            elif key == "items":
                out[key] = convert(value, depth + 1)
            elif key == "anyOf":
                children = [child for child in value if child.get("type") != "null"]
                if len(children) != len(value):
                    out["nullable"] = True
                if len(children) == 1:
                    out.update(convert(children[0], depth + 1))
                else:
                    out[key] = [convert(child, depth + 1) for child in children]
            elif key in ("description", "enum", "required", "format", "minimum", "maximum", "minItems", "maxItems"):
                out[key] = value
            else:
                raise ConfigurationError(f"responseSchema no admite la restriccion {key}.")
        return out

    return convert(schema)


class ModelClient(OllamaClient):
    """Fachada compatible con el cliente previo; modelos y protocolos vienen de .env.

    API compatible: /v1/chat/completions y /v1/embeddings (vLLM/llama.cpp).
    Vertex: /publishers/google/models/{modelo}:generateContent, opt-in cloud.
    """

    def __init__(self, *, client: httpx.Client | None = None, **kwargs: Any) -> None:
        self.settings = get_settings()
        s = self.settings
        providers = (s.llm_provider, s.llm_deep_provider, s.llm_embedding_provider)
        urls = []
        if "ollama" in providers:
            urls.append(s.ollama_base_url)
        if "openai_compatible" in providers:
            urls.append(s.llm_api_base_url)
        if "vertex" in providers:
            if s.llm_local_only:
                raise ConfigurationError("Vertex requiere LLM_LOCAL_ONLY=false: envia datos a cloud.")
            if not s.llm_vertex_base_url.startswith("https://"):
                raise ConfigurationError("LLM_VERTEX_BASE_URL debe ser HTTPS.")
        hosts = {host.strip() for host in s.llm_local_hosts.split(",")}
        for url in urls:
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username:
                raise ConfigurationError("Endpoint de inferencia invalido.")
            if s.llm_local_only and parsed.hostname not in hosts:
                raise ConfigurationError("El endpoint no pertenece a LLM_LOCAL_HOSTS aprobado por TI.")
        if s.llm_local_only and any(
            "cloud" in m.casefold() for m in (s.ollama_fast_model, s.ollama_deep_model, s.ollama_embedding_model)
        ):
            raise ConfigurationError("Los modelos cloud de Ollama estan deshabilitados en modo local.")
        super().__init__(client=client, **kwargs)
        self._vertex_validated: dict[str, float] = {}

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        # Un intento por llamada: HTTP ambiguo no se reenvia automaticamente.
        deadline = _deadline.get()
        remaining = min(self.timeout, self.settings.llm_request_deadline_seconds)
        if deadline is not None:
            remaining = min(remaining, deadline - time.monotonic())
        if remaining <= 0:
            raise OllamaUnavailableError("La consulta alcanzo su tiempo limite.")
        url = path if path.startswith("http") else f"{self.base_url}{path}"
        headers = {}
        if url.startswith(self.settings.llm_api_base_url.rstrip("/") + "/"):
            secret = self.settings.llm_api_key.get_secret_value()
            if secret:
                headers["Authorization"] = f"Bearer {secret}"
        elif self.settings.llm_vertex_base_url and url.startswith(self.settings.llm_vertex_base_url.rstrip("/") + "/"):
            # Se carga google-auth solo cuando TI habilita el adapter cloud.
            import google.auth
            from google.auth.transport.requests import Request

            credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
            credentials.refresh(Request())
            headers["Authorization"] = f"Bearer {credentials.token}"
        with admission("inference", self.settings.inference_max_inflight):
            started = time.monotonic()
            try:
                response = self._client.post(
                    url, json=payload, headers=headers, timeout=httpx.Timeout(remaining, connect=min(10, remaining))
                )
                if response.status_code >= 400:
                    raise OllamaUnavailableError(detail=f"HTTP {response.status_code}")
                data = response.json()
                if time.monotonic() - started > remaining:
                    raise OllamaUnavailableError("La consulta alcanzo su tiempo limite.")
                if not isinstance(data, dict):
                    raise ValueError("respuesta no es objeto")
                return data
            except (httpx.HTTPError, ValueError) as exc:
                raise OllamaUnavailableError("Respuesta de inferencia no valida.", detail=type(exc).__name__) from exc

    def chat(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        num_ctx: int | None = None,
        max_tokens: int | None = None,
        stop: list[str] | None = None,
        response_schema: dict[str, Any] | None = None,
        execution_profile: Literal["fast", "deep"] | None = None,
    ) -> ChatResult:
        s = self.settings
        if execution_profile not in (None, "fast", "deep"):
            raise ConfigurationError("Perfil de inferencia no valido.")
        if execution_profile is not None and model != (
            s.ollama_deep_model if execution_profile == "deep" else s.ollama_fast_model
        ):
            raise ConfigurationError("El modelo no corresponde al perfil de inferencia.")
        # Un mismo checkpoint puede atender ambos perfiles sin perder sus limites.
        deep = execution_profile == "deep" if execution_profile else (
            model == s.ollama_deep_model and model != s.ollama_fast_model
        )
        provider = s.llm_deep_provider if deep else s.llm_provider
        thinking = s.llm_deep_thinking if deep else s.llm_fast_thinking
        if response_schema is not None and s.llm_structured_thinking != "default":
            thinking = s.llm_structured_thinking
        think = None if thinking == "default" else thinking == "enabled"
        top_k = s.llm_deep_top_k if deep else s.llm_fast_top_k
        temperature = s.llm_temperature if temperature is None else temperature
        if response_schema is not None:
            Draft202012Validator.check_schema(response_schema)
        messages = [dict(message) for message in messages]
        if s.llm_system_prefix:
            messages.insert(0, {"role": "system", "content": s.llm_system_prefix})
        started = time.perf_counter()
        if provider == "ollama":
            result = super().chat(
                model=model,
                messages=messages,
                temperature=temperature,
                num_ctx=num_ctx,
                max_tokens=max_tokens,
                stop=stop,
                response_schema=response_schema,
                think=think,
                top_k=top_k,
            )
        elif provider == "openai_compatible":
            payload: dict[str, Any] = {
                "model": model,
                "messages": messages,
                "stream": False,
                "temperature": temperature,
                "top_p": s.llm_top_p,
            }
            if max_tokens is not None:
                payload["max_tokens"] = max_tokens
            if stop:
                payload["stop"] = stop
            if think is not None:
                payload["chat_template_kwargs"] = {"enable_thinking": think}
            if top_k is not None:
                payload["top_k"] = top_k
            if response_schema is not None:
                payload["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {"name": "matrix_response", "schema": response_schema},
                }
            data = self._post(s.llm_api_base_url.rstrip("/") + "/chat/completions", payload)
            choices = data.get("choices") or []
            if (
                not isinstance(choices, list)
                or not choices
                or not isinstance(choices[0], dict)
                or choices[0].get("finish_reason") not in ("stop", None)
            ):
                raise OllamaUnavailableError("El modelo no completo la respuesta.")
            message = choices[0].get("message")
            if not isinstance(message, dict):
                raise OllamaUnavailableError("Respuesta de chat no valida.")
            content = message.get("content")
            # El parser del runtime separa reasoning/reasoning_content. Nunca
            # se usan como fallback de contenido final ni se persisten.
            usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
            result = ChatResult(
                content=content or "", model=model, latency_ms=int((time.perf_counter() - started) * 1000),
                prompt_eval_count=_metric(usage, "prompt_tokens"),
                eval_count=_metric(usage, "completion_tokens"),
            )
        else:
            if think is not None or top_k is not None:
                raise ConfigurationError("Thinking/top_k por perfil requieren un adapter local compatible.")
            config: dict[str, Any] = {"temperature": temperature, "topP": s.llm_top_p}
            if max_tokens is not None:
                config["maxOutputTokens"] = max_tokens
            if stop:
                config["stopSequences"] = stop
            if response_schema is not None:
                config.update(responseMimeType="application/json", responseSchema=vertex_schema(response_schema))
            payload = {
                "contents": [
                    {"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
                    for m in messages
                    if m["role"] != "system"
                ],
                "generationConfig": config,
            }
            systems = [m["content"] for m in messages if m["role"] == "system"]
            if systems:
                payload["systemInstruction"] = {"parts": [{"text": "\n\n".join(systems)}]}
            data = self._post(
                s.llm_vertex_base_url.rstrip("/") + "/" + quote(model, safe="") + ":generateContent", payload
            )
            candidates = data.get("candidates") or []
            if (
                not isinstance(candidates, list)
                or not candidates
                or not isinstance(candidates[0], dict)
                or candidates[0].get("finishReason") != "STOP"
            ):
                raise OllamaUnavailableError("Vertex rechazo o trunco la respuesta.")
            candidate_content = candidates[0].get("content")
            parts = candidate_content.get("parts") if isinstance(candidate_content, dict) else None
            if not isinstance(parts, list) or any(
                not isinstance(part, dict) or not isinstance(part.get("text", ""), str) for part in parts
            ):
                raise OllamaUnavailableError("Vertex devolvio contenido no valido.")
            content = "".join(part.get("text", "") for part in parts if not part.get("thought"))
            result = ChatResult(content=content, model=model, latency_ms=int((time.perf_counter() - started) * 1000))
        if not isinstance(result.content, str) or not result.content.strip():
            raise OllamaUnavailableError("El modelo devolvio una respuesta vacia.")
        if re.search(
            r"</?think>|\[/?THINK\]|<\|channel\|?>|<channel\|>", result.content, re.IGNORECASE
        ):
            raise OllamaUnavailableError("El runtime no separo el razonamiento del contenido final.")
        if response_schema is not None:
            try:
                value = json.loads(result.content)
                Draft202012Validator(response_schema).validate(value)
            except Exception as exc:
                raise OllamaUnavailableError("La respuesta no cumple el schema solicitado.") from exc
        return result

    def embed(self, texts: list[str], *, model: str | None = None) -> list[list[float]]:
        if not texts:
            return []
        if self.settings.llm_embedding_provider == "ollama":
            vectors = super().embed(texts, model=model)
        else:
            data = self._post(
                self.settings.llm_api_base_url.rstrip("/") + "/embeddings",
                {"model": model or self.embedding_model, "input": texts},
            )
            entries = data.get("data") or []
            if (
                not isinstance(entries, list)
                or any(
                    not isinstance(item, dict) or type(item.get("index")) is not int or "embedding" not in item
                    for item in entries
                )
                or sorted(item["index"] for item in entries) != list(range(len(texts)))
            ):
                raise EmbeddingDimensionMismatchError("Indices de embeddings invalidos.")
            vectors = [item["embedding"] for item in sorted(entries, key=lambda item: item["index"])]
        if len(vectors) != len(texts) or any(
            not isinstance(v, list)
            or len(v) != self.expected_dimension
            or any(isinstance(n, bool) or not isinstance(n, float | int) or not math.isfinite(n) for n in v)
            for v in vectors
        ):
            raise EmbeddingDimensionMismatchError()
        return vectors

    def embedding_revision(self) -> str:
        if self.settings.llm_embedding_provider == "ollama":
            # Digest real: una etiqueta latest que cambia invalida el indice.
            digest = dict(super().list_models().digests).get(self.embedding_model)
            if not digest:
                raise ConfigurationError("Ollama no reporto digest del modelo de embeddings.")
            return digest
        revision = self.settings.llm_embedding_revision
        if not revision or revision == "unverified":
            raise ConfigurationError("LLM_EMBEDDING_REVISION es obligatoria para el runtime compatible.")
        return revision

    def probe_embedding_dimension(self, *, model: str | None = None) -> int:
        return len(self.embed(["matrix rh dimension probe"], model=model)[0])

    def ping(self) -> bool:
        try:
            self.list_models()
            return True
        except Exception:
            return False

    def list_models(self) -> ModelInventory:
        s = self.settings
        names, digests = [], []
        if "ollama" in (s.llm_provider, s.llm_deep_provider, s.llm_embedding_provider):
            inventory = super().list_models()
            names.extend(inventory.names)
            digests.extend(inventory.digests)
            for provider, model, expected in (
                (s.llm_provider, s.ollama_fast_model, s.llm_fast_digest),
                (s.llm_deep_provider, s.ollama_deep_model, s.llm_deep_digest),
                (s.llm_embedding_provider, s.ollama_embedding_model, s.llm_embedding_digest),
            ):
                if provider == "ollama" and expected and dict(inventory.digests).get(model) != expected:
                    raise ConfigurationError("El digest del modelo no coincide con .env.")
        if "openai_compatible" in (s.llm_provider, s.llm_deep_provider, s.llm_embedding_provider):
            headers = (
                {"Authorization": f"Bearer {s.llm_api_key.get_secret_value()}"}
                if s.llm_api_key.get_secret_value()
                else {}
            )
            response = self._client.get(s.llm_api_base_url.rstrip("/") + "/models", headers=headers, timeout=10)
            response.raise_for_status()
            names.extend(str(model["id"]) for model in response.json().get("data", []))
        # Sonda sintetica solo con opt-in cloud; cache de cinco minutos por proceso.
        for provider, model in ((s.llm_provider, s.ollama_fast_model), (s.llm_deep_provider, s.ollama_deep_model)):
            if provider == "vertex":
                if self._vertex_validated.get(model, 0) < time.monotonic():
                    self.chat(
                        model=model,
                        messages=[{"role": "user", "content": "Reply only OK."}],
                        temperature=0,
                        max_tokens=128,
                    )
                    self._vertex_validated[model] = time.monotonic() + 300
                names.append(model)
        return ModelInventory(names=tuple(names), digests=tuple(digests))
