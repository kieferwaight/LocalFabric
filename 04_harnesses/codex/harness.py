"""Harness for the OpenAI Codex surface (CLI / API) via the `openai` SDK."""

from __future__ import annotations

import os
from collections import deque
from typing import Any, Deque, Dict, Iterator, Mapping, Optional

from harnesses.base import Harness, HarnessError, HarnessStatus


class CodexHarness(Harness):
    """Wraps the `openai` SDK pointed at the Codex CLI or hosted Codex endpoint.

    Codex shares the OpenAI wire format but is code-tuned and may be served by a
    local Codex CLI proxy. ``base_url`` can be set to that proxy; otherwise the
    harness falls through to the hosted OpenAI endpoint.

    Config keys:
        api_key:    Defaults to ``CODEX_API_KEY`` then ``OPENAI_API_KEY``.
        model:      Default ``gpt-4.1-mini`` (code-class).
        base_url:   Override (e.g. ``http://localhost:1455/v1`` for a Codex CLI).
        timeout:    Request timeout seconds (default 120 — code tasks are slow).
    """

    name = "codex"

    def __init__(self, config: Optional[Mapping[str, Any]] = None) -> None:
        super().__init__(config)
        self._client: Optional[Any] = None
        self._request_ids: Deque[str] = deque(maxlen=64)
        self.model: str = self.config.get("model", "gpt-4.1-mini")
        self.timeout: float = float(self.config.get("timeout", 120))
        self.base_url: Optional[str] = self.config.get("base_url")

    # ----------------------------------------------------------------- internals
    def _ensure_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            from openai import OpenAI  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise HarnessError("openai SDK is not installed") from exc

        api_key = (
            self.config.get("api_key")
            or os.environ.get("CODEX_API_KEY")
            or os.environ.get("OPENAI_API_KEY")
        )
        if not api_key and not self.base_url:
            raise HarnessError("CODEX_API_KEY / OPENAI_API_KEY is not set")

        kwargs: Dict[str, Any] = {"api_key": api_key or "local", "timeout": self.timeout}
        if self.base_url:
            kwargs["base_url"] = self.base_url
        self._client = OpenAI(**kwargs)
        return self._client

    def _build_chat_kwargs(self, request: Mapping[str, Any]) -> Dict[str, Any]:
        messages = request.get("messages")
        if messages is None:
            messages = [{"role": "user", "content": request.get("prompt", "")}]
        kwargs: Dict[str, Any] = {
            "model": request.get("model", self.model),
            "messages": list(messages),
        }
        for key in ("temperature", "top_p", "max_tokens", "tools", "tool_choice", "stop"):
            if key in request:
                kwargs[key] = request[key]
        return kwargs

    # ----------------------------------------------------------------- lifecycle
    def start(self) -> HarnessStatus:
        self._ensure_client()
        return self._set_state("running", "codex client ready")

    def stop(self) -> HarnessStatus:
        self._client = None
        return self._set_state("stopped")

    def status(self) -> HarnessStatus:
        return HarnessStatus(
            name=self.name,
            state=self._state,
            detail=f"model={self.model} base_url={self.base_url or 'default'}",
            metadata={"model": self.model, "request_ids": list(self._request_ids)},
        )

    # ------------------------------------------------------------------ requests
    def invoke(self, request: Mapping[str, Any]) -> Dict[str, Any]:
        client = self._ensure_client()
        kwargs = self._build_chat_kwargs(request)
        try:
            response = client.chat.completions.create(**kwargs)
        except Exception as exc:  # noqa: BLE001
            self._record(f"invoke error: {exc}")
            raise HarnessError(f"codex invoke failed: {exc}") from exc

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

    def stream(self, request: Mapping[str, Any]) -> Iterator[Dict[str, Any]]:
        client = self._ensure_client()
        kwargs = self._build_chat_kwargs(request)
        kwargs["stream"] = True
        try:
            for chunk in client.chat.completions.create(**kwargs):
                yield chunk.model_dump() if hasattr(chunk, "model_dump") else dict(chunk)
            self._record("stream ok")
        except Exception as exc:  # noqa: BLE001
            self._record(f"stream error: {exc}")
            raise HarnessError(f"codex stream failed: {exc}") from exc

    # ---------------------------------------------------------------- observers
    def logs(self, tail: int = 50) -> list[str]:
        return list(self._logs)[-tail:]

    def health(self) -> HarnessStatus:
        try:
            client = self._ensure_client()
            client.models.list()
            return HarnessStatus(name=self.name, state="ready", detail="codex reachable")
        except Exception as exc:  # noqa: BLE001
            return HarnessStatus(name=self.name, state="error", detail=str(exc))
