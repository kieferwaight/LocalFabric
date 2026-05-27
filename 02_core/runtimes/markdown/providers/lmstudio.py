"""LM Studio provider for the markdown harness.

Wraps ``harnesses.lmstudio.LMStudioHarness`` so the markdown harness can
dispatch ``provider: lmstudio`` frontmatter files to a local LM Studio
server. Vision prompts attach image bytes via the OpenAI-compatible
``image_url`` content blocks (``data:<mime>;base64,<...>``).
"""

from __future__ import annotations

import base64
import mimetypes
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

from harnesses.base import HarnessError

from .base import MarkdownProvider, ProviderError, ProviderResult


class LMStudioProvider(MarkdownProvider):
    name = "lmstudio"
    default_model = "local-model"

    def __init__(
        self,
        harness: Any | None = None,
        *,
        config: Mapping[str, Any] | None = None,
    ) -> None:
        self._injected_harness = harness
        self._config: dict[str, Any] = dict(config or {})
        self._harness: Any | None = harness

    # ----------------------------------------------------------------- helpers
    def _ensure_harness(self, model: str | None) -> Any:
        if self._harness is not None:
            return self._harness
        from harnesses.lmstudio import LMStudioHarness

        config = dict(self._config)
        if model and "model" not in config:
            config["model"] = model
        # Provider path assumes the workflow's start step has already spun up
        # the server; skip the auto-spawn to avoid surprising the caller.
        config.setdefault("manage_server", False)
        self._harness = LMStudioHarness(config=config)
        return self._harness

    @staticmethod
    def _encode_image(path: str) -> str:
        p = Path(path)
        mime, _ = mimetypes.guess_type(p.name)
        if mime is None:
            mime = "image/png"
        data = base64.standard_b64encode(p.read_bytes()).decode("ascii")
        return f"data:{mime};base64,{data}"

    @staticmethod
    def _extract_text(response: Mapping[str, Any]) -> str:
        choices = response.get("choices") or []
        if not choices:
            return ""
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        if isinstance(message, dict) and isinstance(message.get("content"), str):
            return message["content"]
        return ""

    @staticmethod
    def _extract_stream_text(event: Mapping[str, Any]) -> str:
        choices = event.get("choices") or []
        if not choices:
            return ""
        delta = choices[0].get("delta") if isinstance(choices[0], dict) else None
        if isinstance(delta, dict) and isinstance(delta.get("content"), str):
            return delta["content"]
        return ""

    def _build_messages(
        self,
        prompt: str,
        *,
        system: str | None,
        images: list[str] | None,
    ) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        if system:
            messages.append({"role": "system", "content": system})
        if images:
            content_blocks: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
            for path in images:
                content_blocks.append(
                    {"type": "image_url", "image_url": {"url": self._encode_image(path)}}
                )
            messages.append({"role": "user", "content": content_blocks})
        else:
            messages.append({"role": "user", "content": prompt})
        return messages

    # ------------------------------------------------------------------- public
    def run(
        self,
        prompt: str,
        *,
        model: str | None = None,
        system: str | None = None,
        stream: bool = False,
        max_tokens: int | None = None,
        temperature: float | None = None,
        images: list[str] | None = None,
        stop: list[str] | None = None,
        options: dict[str, Any] | None = None,
    ) -> ProviderResult | Iterator[str]:
        effective_model = model or self.default_model
        harness = self._ensure_harness(effective_model)
        messages = self._build_messages(prompt, system=system, images=images)

        request: dict[str, Any] = {"model": effective_model, "messages": messages}
        if max_tokens is not None:
            request["max_tokens"] = int(max_tokens)
        if temperature is not None:
            request["temperature"] = float(temperature)
        if stop:
            request["stop"] = list(stop)
        if options:
            # OpenAI-compatible passthrough — `top_p`, `presence_penalty`, etc.
            for key, value in options.items():
                request.setdefault(key, value)

        if stream:
            return self._stream(harness, request)

        try:
            response = harness.invoke(request)
        except HarnessError as exc:
            raise ProviderError(f"lmstudio provider failed: {exc}") from exc

        text = self._extract_text(response)
        return ProviderResult(
            text=text,
            model=str(response.get("model") or effective_model),
            usage=dict(response.get("usage") or {}),
            raw=dict(response),
        )

    def _stream(self, harness: Any, request: Mapping[str, Any]) -> Iterator[str]:
        try:
            for event in harness.stream(request):
                chunk = self._extract_stream_text(event)
                if chunk:
                    yield chunk
        except HarnessError as exc:
            raise ProviderError(f"lmstudio provider failed: {exc}") from exc
