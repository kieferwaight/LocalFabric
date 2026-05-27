"""Harness for Google Gemini via the `google-generativeai` SDK."""

from __future__ import annotations

import os
import uuid
from collections import deque
from collections.abc import Iterator, Mapping
from typing import Any

from harnesses.base import Harness, HarnessError, HarnessStatus


class GeminiHarness(Harness):
    """Wraps `google.generativeai` as a lifecycle-controlled harness.

    Config keys:
        api_key:    Defaults to ``GOOGLE_API_KEY`` then ``GEMINI_API_KEY`` env.
        model:      Model id (default ``gemini-1.5-flash``).
        timeout:    Request timeout in seconds (default 60).
        safety_settings, generation_config: passed through to the SDK.

    Like the other hosted harnesses, ``start``/``stop`` simply manage the SDK
    client instance. ``health`` issues a tiny ``generate_content`` ping.
    """

    name = "gemini"

    def __init__(self, config: Mapping[str, Any] | None = None) -> None:
        super().__init__(config)
        self._genai: Any | None = None
        self._model_instance: Any | None = None
        self._request_ids: deque[str] = deque(maxlen=64)
        self.model: str = self.config.get("model", "gemini-1.5-flash")
        self.timeout: float = float(self.config.get("timeout", 60))

    # ----------------------------------------------------------------- internals
    def _ensure_model(self) -> Any:
        if self._model_instance is not None:
            return self._model_instance
        try:
            import google.generativeai as genai  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise HarnessError(
                "google-generativeai SDK is not installed — run `uv sync --extra llm`."
            ) from exc

        api_key = (
            self.config.get("api_key")
            or os.environ.get("GOOGLE_API_KEY")
            or os.environ.get("GEMINI_API_KEY")
        )
        if not api_key:
            raise HarnessError("GOOGLE_API_KEY / GEMINI_API_KEY is not set")
        genai.configure(api_key=api_key)
        self._genai = genai

        gen_kwargs: dict[str, Any] = {}
        if self.config.get("generation_config"):
            gen_kwargs["generation_config"] = self.config["generation_config"]
        if self.config.get("safety_settings"):
            gen_kwargs["safety_settings"] = self.config["safety_settings"]
        if self.config.get("system_instruction"):
            gen_kwargs["system_instruction"] = self.config["system_instruction"]
        self._model_instance = genai.GenerativeModel(self.model, **gen_kwargs)
        return self._model_instance

    def _coerce_contents(self, request: Mapping[str, Any]) -> Any:
        if "contents" in request:
            return request["contents"]
        messages = request.get("messages")
        if messages is not None:
            # Translate OpenAI-style messages → Gemini "contents" format.
            converted: list[dict[str, Any]] = []
            for msg in messages:
                role = "user" if msg.get("role") == "user" else "model"
                content = msg.get("content", "")
                if isinstance(content, str):
                    parts = [{"text": content}]
                else:
                    parts = list(content)
                converted.append({"role": role, "parts": parts})
            return converted
        return request.get("prompt", "")

    # ----------------------------------------------------------------- lifecycle
    def start(self) -> HarnessStatus:
        self._ensure_model()
        return self._set_state("running", "gemini client ready")

    def stop(self) -> HarnessStatus:
        self._model_instance = None
        self._genai = None
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
        model = self._ensure_model()
        contents = self._coerce_contents(request)
        try:
            response = model.generate_content(contents)
        except Exception as exc:  # noqa: BLE001
            self._record(f"invoke error: {exc}")
            raise HarnessError(f"gemini invoke failed: {exc}") from exc

        rid = uuid.uuid4().hex  # google SDK does not expose a request id directly
        self._request_ids.append(rid)
        self._record(f"invoke ok id={rid}")
        candidates = getattr(response, "candidates", []) or []
        return {
            "id": rid,
            "model": self.model,
            "text": getattr(response, "text", ""),
            "candidates": [
                {"finish_reason": getattr(c, "finish_reason", None)} for c in candidates
            ],
            "usage": getattr(response, "usage_metadata", None).__dict__
            if getattr(response, "usage_metadata", None) is not None
            else {},
        }

    def stream(self, request: Mapping[str, Any]) -> Iterator[dict[str, Any]]:
        model = self._ensure_model()
        contents = self._coerce_contents(request)
        try:
            response_iter = model.generate_content(contents, stream=True)
            for chunk in response_iter:
                yield {
                    "text": getattr(chunk, "text", ""),
                    "candidates": getattr(chunk, "candidates", None) is not None,
                }
            self._record("stream ok")
        except Exception as exc:  # noqa: BLE001
            self._record(f"stream error: {exc}")
            raise HarnessError(f"gemini stream failed: {exc}") from exc

    # ---------------------------------------------------------------- observers
    def logs(self, tail: int = 50) -> list[str]:
        return list(self._logs)[-tail:]

    def health(self) -> HarnessStatus:
        try:
            model = self._ensure_model()
            model.generate_content("ping")
            return HarnessStatus(name=self.name, state="ready", detail="api reachable")
        except Exception as exc:  # noqa: BLE001
            return HarnessStatus(name=self.name, state="error", detail=str(exc))
