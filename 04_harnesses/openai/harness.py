"""Harness for the OpenAI Chat Completions API via the official `openai` SDK."""

from __future__ import annotations

import os
from collections import deque
from collections.abc import Iterator, Mapping
from typing import Any

from harnesses.base import Harness, HarnessError, HarnessStatus


class OpenAIHarness(Harness):
    """Wraps the `openai` Python SDK against OpenAI's hosted endpoints.

    Config keys:
        api_key:    API key (defaults to ``OPENAI_API_KEY`` env).
        organization, project: optional OpenAI account scoping.
        model:      Model id (default ``gpt-4o-mini``).
        base_url:   Override base URL (e.g. for OpenAI-compatible proxies).
        timeout:    Request timeout seconds (default 60).
    """

    name = "openai"
    _default_model = "gpt-4o-mini"
    _default_base_url: str | None = None  # SDK default
    _api_key_env = "OPENAI_API_KEY"

    def __init__(self, config: Mapping[str, Any] | None = None) -> None:
        super().__init__(config)
        self._client: Any | None = None
        self._request_ids: deque[str] = deque(maxlen=64)
        self.model: str = self.config.get("model", self._default_model)
        self.timeout: float = float(self.config.get("timeout", 60))

    # ----------------------------------------------------------------- internals
    def _ensure_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            from openai import OpenAI  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise HarnessError("openai SDK is not installed — run `uv sync --extra llm`.") from exc

        api_key = self.config.get("api_key") or os.environ.get(self._api_key_env)
        if not api_key and not self.config.get("allow_anonymous"):
            raise HarnessError(f"{self._api_key_env} is not set")

        kwargs: dict[str, Any] = {"api_key": api_key or "missing", "timeout": self.timeout}
        base_url = self.config.get("base_url", self._default_base_url)
        if base_url:
            kwargs["base_url"] = base_url
        if self.config.get("organization"):
            kwargs["organization"] = self.config["organization"]
        if self.config.get("project"):
            kwargs["project"] = self.config["project"]

        self._client = OpenAI(**kwargs)
        return self._client

    def _build_chat_kwargs(self, request: Mapping[str, Any]) -> dict[str, Any]:
        messages = request.get("messages")
        if messages is None:
            messages = [{"role": "user", "content": request.get("prompt", "")}]
        kwargs: dict[str, Any] = {
            "model": request.get("model", self.model),
            "messages": list(messages),
        }
        for key in (
            "temperature",
            "top_p",
            "max_tokens",
            "tools",
            "tool_choice",
            "response_format",
            "seed",
            "stop",
        ):
            if key in request:
                kwargs[key] = request[key]
        return kwargs

    # ----------------------------------------------------------------- lifecycle
    def start(self) -> HarnessStatus:
        self._ensure_client()
        return self._set_state("running", f"{self.name} client ready")

    def stop(self) -> HarnessStatus:
        self._client = None
        return self._set_state("stopped")

    def status(self) -> HarnessStatus:
        return HarnessStatus(
            name=self.name,
            state=self._state,
            detail=f"model={self.model}",
            metadata={"model": self.model, "request_ids": list(self._request_ids)},
        )

    # ------------------------------------------------------------------ requests
    def invoke(self, request: Mapping[str, Any]) -> dict[str, Any]:
        client = self._ensure_client()
        kwargs = self._build_chat_kwargs(request)
        try:
            response = client.chat.completions.create(**kwargs)
        except Exception as exc:  # noqa: BLE001
            self._record(f"invoke error: {exc}")
            raise HarnessError(f"{self.name} invoke failed: {exc}") from exc

        rid = getattr(response, "id", "") or ""
        if rid:
            self._request_ids.append(rid)
        self._record(f"invoke ok id={rid}")
        return {
            "id": rid,
            "model": getattr(response, "model", self.model),
            "choices": [c.model_dump() for c in getattr(response, "choices", [])],
            "usage": getattr(getattr(response, "usage", None), "model_dump", lambda: {})(),
        }

    def stream(self, request: Mapping[str, Any]) -> Iterator[dict[str, Any]]:
        client = self._ensure_client()
        kwargs = self._build_chat_kwargs(request)
        kwargs["stream"] = True
        try:
            for chunk in client.chat.completions.create(**kwargs):
                yield chunk.model_dump() if hasattr(chunk, "model_dump") else dict(chunk)
            self._record("stream ok")
        except Exception as exc:  # noqa: BLE001
            self._record(f"stream error: {exc}")
            raise HarnessError(f"{self.name} stream failed: {exc}") from exc

    # ---------------------------------------------------------------- observers
    def logs(self, tail: int = 50) -> list[str]:
        return list(self._logs)[-tail:]

    def health(self) -> HarnessStatus:
        try:
            client = self._ensure_client()
            # `models.list` is the canonical cheap reachability check.
            client.models.list()
            return HarnessStatus(name=self.name, state="ready", detail="api reachable")
        except Exception as exc:  # noqa: BLE001
            return HarnessStatus(name=self.name, state="error", detail=str(exc))
