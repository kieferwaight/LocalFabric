"""Markdown provider for the ``claude_cli`` transport.

Wraps ``harnesses.claude_cli.ClaudeCliHarness`` so the markdown harness
can dispatch ``provider: claude_cli`` frontmatter files to the locally
installed ``claude`` binary. This is a separate channel from
:class:`core.runtimes.markdown.providers.ClaudeProvider`, which uses the
Anthropic SDK directly — they coexist so callers can pick the transport
that fits the task without changing the prompt body.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any

from harnesses.base import HarnessError

from .base import MarkdownProvider, ProviderError, ProviderResult


class ClaudeCliProvider(MarkdownProvider):
    """Markdown provider backed by ``ClaudeCliHarness``."""

    name = "claude_cli"
    default_model: str = "claude-sonnet-4-6"
    #: Class-level capability flag — checked at the top of :meth:`run`
    #: so unsupported-image requests fail before any subprocess spawn.
    supports_images: bool = True

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
        from harnesses.claude_cli import ClaudeCliHarness

        config = dict(self._config)
        if model and "model" not in config:
            config["model"] = model
        self._harness = ClaudeCliHarness(config=config)
        return self._harness

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
        if images and not self.supports_images:
            raise ProviderError(f"{self.name} does not support images")

        effective_model = model or self.default_model
        harness = self._ensure_harness(effective_model)

        body = prompt
        if system:
            body = f"{system}\n\n{body}"

        request: dict[str, Any] = {"prompt": body, "model": effective_model}
        if images:
            request["images"] = list(images)

        if stream:
            return self._stream(harness, request)

        try:
            response = harness.invoke(request)
        except HarnessError as exc:
            raise ProviderError(f"{self.name} provider failed: {exc}") from exc

        return ProviderResult(
            text=str(response.get("text", "")),
            model=str(response.get("model") or effective_model),
            usage={},
            raw=dict(response),
        )

    def _stream(self, harness: Any, request: Mapping[str, Any]) -> Iterator[str]:
        try:
            for event in harness.stream(request):
                chunk = event.get("text") if isinstance(event, dict) else None
                if isinstance(chunk, str) and chunk:
                    yield chunk
        except HarnessError as exc:
            raise ProviderError(f"{self.name} provider failed: {exc}") from exc
