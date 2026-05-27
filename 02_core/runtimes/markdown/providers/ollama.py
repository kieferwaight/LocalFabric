"""Ollama provider for the markdown harness.

Wraps ``harnesses.ollama.OllamaHarness`` so the markdown harness can dispatch
``provider: ollama`` frontmatter files to a local Ollama server. Vision
prompts attach image bytes via the ``images:`` frontmatter list — Ollama's
native chat API accepts base64-encoded images directly on the message.
"""

from __future__ import annotations

import base64
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

from harnesses.base import HarnessError

from .base import MarkdownProvider, ProviderError, ProviderResult


class OllamaProvider(MarkdownProvider):
    name = "ollama"
    default_model = "llama3.2"

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
        from harnesses.ollama import OllamaHarness

        config = dict(self._config)
        if model and "model" not in config:
            config["model"] = model
        # Default to not auto-spawning `ollama serve` from the provider path —
        # the workflow's start step handles lifecycle. Callers can override.
        config.setdefault("manage_server", False)
        # Vision models pay a first-call cost loading 7+ GB of weights into RAM.
        # Bump the default well above the 120s harness default so the first
        # inference doesn't time out.
        config.setdefault("timeout", 300)
        self._harness = OllamaHarness(config=config)
        return self._harness

    @staticmethod
    def _encode_image(path: str) -> str:
        with Path(path).open("rb") as handle:
            return base64.standard_b64encode(handle.read()).decode("ascii")

    @staticmethod
    def _extract_text(response: Mapping[str, Any]) -> str:
        message = response.get("message") or {}
        if isinstance(message, dict) and isinstance(message.get("content"), str):
            return message["content"]
        if isinstance(response.get("response"), str):
            return response["response"]
        return ""

    def _build_message(
        self,
        prompt: str,
        *,
        images: list[str] | None,
    ) -> dict[str, Any]:
        message: dict[str, Any] = {"role": "user", "content": prompt}
        if images:
            message["images"] = [self._encode_image(p) for p in images]
        return message

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
        messages: list[dict[str, Any]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append(self._build_message(prompt, images=images))

        merged_options: dict[str, Any] = dict(options or {})
        if temperature is not None:
            merged_options.setdefault("temperature", float(temperature))
        if max_tokens is not None:
            merged_options.setdefault("num_predict", int(max_tokens))
        if stop:
            merged_options.setdefault("stop", list(stop))

        request: dict[str, Any] = {
            "model": effective_model,
            "messages": messages,
        }
        if merged_options:
            request["options"] = merged_options

        if stream:
            return self._stream(harness, request)

        try:
            response = harness.invoke(request)
        except HarnessError as exc:
            raise ProviderError(f"ollama provider failed: {exc}") from exc

        text = self._extract_text(response)
        usage = {
            k: response[k]
            for k in ("prompt_eval_count", "eval_count", "total_duration")
            if k in response
        }
        return ProviderResult(
            text=text,
            model=str(response.get("model") or effective_model),
            usage=usage,
            raw=dict(response),
        )

    def _stream(self, harness: Any, request: Mapping[str, Any]) -> Iterator[str]:
        try:
            for event in harness.stream(request):
                message = event.get("message") if isinstance(event, dict) else None
                if isinstance(message, dict):
                    chunk = message.get("content")
                    if isinstance(chunk, str) and chunk:
                        yield chunk
        except HarnessError as exc:
            raise ProviderError(f"ollama provider failed: {exc}") from exc
