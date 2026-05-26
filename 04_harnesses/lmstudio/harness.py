"""Harness for an LM Studio local server — OpenAI-compatible HTTP endpoint."""

from __future__ import annotations

import os
from collections import deque
from collections.abc import Iterator, Mapping
from typing import Any

from harnesses.base import Harness, HarnessError, HarnessStatus


class LMStudioHarness(Harness):
    """Talks to an LM Studio local server using the `openai` SDK.

    LM Studio exposes an OpenAI-compatible API, by default at
    ``http://localhost:1234/v1``. The user is responsible for launching the
    LM Studio app — ``start``/``stop`` here only manage the SDK client.
    ``status`` and ``health`` perform a reachability check against ``/models``.

    Config keys:
        base_url:   Default ``http://localhost:1234/v1``.
        api_key:    Default ``lm-studio`` (LM Studio ignores it but the SDK
                    requires *some* value). Falls back to ``LMSTUDIO_API_KEY``.
        model:      Loaded model id (default ``local-model``).
        timeout:    Default 120s (local models can be slow on first load).
    """

    name = "lmstudio"
    DEFAULT_BASE_URL = "http://localhost:1234/v1"

    def __init__(self, config: Mapping[str, Any] | None = None) -> None:
        super().__init__(config)
        self._client: Any | None = None
        self._request_ids: deque[str] = deque(maxlen=64)
        self.base_url: str = self.config.get("base_url", self.DEFAULT_BASE_URL)
        self.api_key: str = (
            self.config.get("api_key") or os.environ.get("LMSTUDIO_API_KEY") or "lm-studio"
        )
        self.model: str = self.config.get("model", "local-model")
        self.timeout: float = float(self.config.get("timeout", 120))

    # ----------------------------------------------------------------- internals
    def _ensure_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            from openai import OpenAI  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise HarnessError("openai SDK is not installed") from exc
        self._client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
        )
        return self._client

    def _build_chat_kwargs(self, request: Mapping[str, Any]) -> dict[str, Any]:
        messages = request.get("messages")
        if messages is None:
            messages = [{"role": "user", "content": request.get("prompt", "")}]
        kwargs: dict[str, Any] = {
            "model": request.get("model", self.model),
            "messages": list(messages),
        }
        for key in ("temperature", "top_p", "max_tokens", "stop"):
            if key in request:
                kwargs[key] = request[key]
        return kwargs

    # ----------------------------------------------------------------- lifecycle
    def start(self) -> HarnessStatus:
        self._ensure_client()
        return self._set_state("running", f"client -> {self.base_url}")

    def stop(self) -> HarnessStatus:
        self._client = None
        return self._set_state("stopped")

    def status(self) -> HarnessStatus:
        return HarnessStatus(
            name=self.name,
            state=self._state,
            detail=f"base_url={self.base_url} model={self.model}",
            metadata={
                "base_url": self.base_url,
                "model": self.model,
                "request_ids": list(self._request_ids),
            },
        )

    # ------------------------------------------------------------------ requests
    def invoke(self, request: Mapping[str, Any]) -> dict[str, Any]:
        client = self._ensure_client()
        kwargs = self._build_chat_kwargs(request)
        try:
            response = client.chat.completions.create(**kwargs)
        except Exception as exc:  # noqa: BLE001
            self._record(f"invoke error: {exc}")
            raise HarnessError(f"lmstudio invoke failed: {exc}") from exc

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
            raise HarnessError(f"lmstudio stream failed: {exc}") from exc

    # ---------------------------------------------------------------- observers
    def logs(self, tail: int = 50) -> list[str]:
        return list(self._logs)[-tail:]

    def health(self) -> HarnessStatus:
        try:
            client = self._ensure_client()
            client.models.list()
            return HarnessStatus(name=self.name, state="ready", detail="lmstudio reachable")
        except Exception as exc:  # noqa: BLE001
            return HarnessStatus(name=self.name, state="error", detail=str(exc))
