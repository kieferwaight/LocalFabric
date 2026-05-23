"""Harness for the Anthropic Claude API via the official `anthropic` SDK."""

from __future__ import annotations

import os
from collections import deque
from typing import Any, Deque, Dict, Iterator, Mapping, Optional

from harnesses.base import Harness, HarnessError, HarnessStatus


class ClaudeHarness(Harness):
    """Wraps the `anthropic` Python SDK as a harness.

    Config keys:
        api_key:    Anthropic API key (defaults to ``ANTHROPIC_API_KEY`` env).
        model:      Model id (default ``claude-sonnet-4-5``).
        base_url:   Override base URL (default: SDK default).
        timeout:    Request timeout in seconds (default 60).
        max_tokens: Default max output tokens (default 1024).

    ``start``/``stop``/``status`` are effectively no-ops — the API is remote.
    ``health`` issues a lightweight Messages call to verify auth and reachability.
    """

    name = "claude"

    def __init__(self, config: Optional[Mapping[str, Any]] = None) -> None:
        super().__init__(config)
        self._client: Optional[Any] = None
        self._request_ids: Deque[str] = deque(maxlen=64)
        self.model: str = self.config.get("model", "claude-sonnet-4-5")
        self.timeout: float = float(self.config.get("timeout", 60))
        self.max_tokens: int = int(self.config.get("max_tokens", 1024))

    # ----------------------------------------------------------------- internals
    def _ensure_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            import anthropic  # type: ignore
        except ImportError as exc:  # pragma: no cover - env-dependent
            raise HarnessError("anthropic SDK is not installed") from exc

        api_key = self.config.get("api_key") or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise HarnessError("ANTHROPIC_API_KEY is not set")

        kwargs: Dict[str, Any] = {"api_key": api_key, "timeout": self.timeout}
        if self.config.get("base_url"):
            kwargs["base_url"] = self.config["base_url"]
        self._client = anthropic.Anthropic(**kwargs)
        return self._client

    def _build_messages_kwargs(self, request: Mapping[str, Any]) -> Dict[str, Any]:
        messages = request.get("messages")
        if messages is None:
            prompt = request.get("prompt", "")
            messages = [{"role": "user", "content": prompt}]
        kwargs: Dict[str, Any] = {
            "model": request.get("model", self.model),
            "messages": list(messages),
            "max_tokens": int(request.get("max_tokens", self.max_tokens)),
        }
        if "system" in request:
            kwargs["system"] = request["system"]
        if "temperature" in request:
            kwargs["temperature"] = request["temperature"]
        if "tools" in request:
            kwargs["tools"] = request["tools"]
        return kwargs

    # ----------------------------------------------------------------- lifecycle
    def start(self) -> HarnessStatus:
        self._ensure_client()
        return self._set_state("running", "anthropic client ready")

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
    def invoke(self, request: Mapping[str, Any]) -> Dict[str, Any]:
        client = self._ensure_client()
        kwargs = self._build_messages_kwargs(request)
        try:
            response = client.messages.create(**kwargs)
        except Exception as exc:  # noqa: BLE001 — surface as HarnessError
            self._record(f"invoke error: {exc}")
            raise HarnessError(f"claude invoke failed: {exc}") from exc

        rid = getattr(response, "id", "") or ""
        if rid:
            self._request_ids.append(rid)
        self._record(f"invoke ok id={rid}")
        return {
            "id": rid,
            "model": getattr(response, "model", self.model),
            "content": [block.model_dump() for block in getattr(response, "content", [])],
            "stop_reason": getattr(response, "stop_reason", None),
            "usage": getattr(getattr(response, "usage", None), "model_dump", lambda: {})(),
        }

    def stream(self, request: Mapping[str, Any]) -> Iterator[Dict[str, Any]]:
        client = self._ensure_client()
        kwargs = self._build_messages_kwargs(request)
        try:
            with client.messages.stream(**kwargs) as stream:
                for event in stream:
                    payload = getattr(event, "model_dump", lambda: {"type": str(event)})()
                    yield payload
                final = stream.get_final_message()
                rid = getattr(final, "id", "") or ""
                if rid:
                    self._request_ids.append(rid)
                self._record(f"stream ok id={rid}")
        except Exception as exc:  # noqa: BLE001
            self._record(f"stream error: {exc}")
            raise HarnessError(f"claude stream failed: {exc}") from exc

    # ---------------------------------------------------------------- observers
    def logs(self, tail: int = 50) -> list[str]:
        return list(self._logs)[-tail:]

    def health(self) -> HarnessStatus:
        try:
            client = self._ensure_client()
            client.messages.create(
                model=self.model,
                max_tokens=1,
                messages=[{"role": "user", "content": "ping"}],
            )
            return HarnessStatus(name=self.name, state="ready", detail="api reachable")
        except Exception as exc:  # noqa: BLE001
            return HarnessStatus(name=self.name, state="error", detail=str(exc))
