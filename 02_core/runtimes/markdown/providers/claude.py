"""Claude provider for the markdown harness.

Wraps ``harnesses.claude.ClaudeHarness`` so the markdown harness can dispatch
``provider: claude`` frontmatter files to the Anthropic Messages API. All
SDK and API-key handling lives in ``ClaudeHarness`` — this module only
translates between the markdown-harness contract and the harness's
``invoke``/``stream`` calls.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any

from harnesses.base import HarnessError

from .base import MarkdownProvider, ProviderError, ProviderResult


class ClaudeProvider(MarkdownProvider):
    """Markdown provider backed by ``ClaudeHarness``.

    The harness is constructed lazily on first call so importing this module
    never requires the ``anthropic`` SDK to be installed. Tests can inject a
    pre-built harness through the constructor.
    """

    name = "claude"
    default_model = "claude-sonnet-4-6"

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
        # Local import keeps `ClaudeHarness` (and its `anthropic` dependency)
        # out of import-time for callers that never touch the claude path.
        from harnesses.claude import ClaudeHarness

        config = dict(self._config)
        if model and "model" not in config:
            config["model"] = model
        self._harness = ClaudeHarness(config=config)
        return self._harness

    @staticmethod
    def _extract_text(response: Mapping[str, Any]) -> str:
        # ClaudeHarness.invoke returns a dict whose `content` is a list of
        # content blocks. Concatenate the `text` of every block whose type
        # is `text`; ignore tool-use / image blocks for the markdown
        # harness's plain-text contract.
        parts: list[str] = []
        for block in response.get("content", []) or []:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text" and isinstance(block.get("text"), str):
                parts.append(block["text"])
        return "".join(parts)

    @staticmethod
    def _extract_stream_text(event: Mapping[str, Any]) -> str:
        """Pull text deltas out of a streaming event payload.

        The Anthropic SDK emits a sequence of typed events while streaming.
        We only care about `content_block_delta` events whose `delta.type`
        is `text_delta` — those carry the incremental text the CLI prints.
        """
        if event.get("type") != "content_block_delta":
            return ""
        delta = event.get("delta") or {}
        if not isinstance(delta, dict):
            return ""
        if delta.get("type") != "text_delta":
            return ""
        text = delta.get("text")
        return text if isinstance(text, str) else ""

    def _build_request(
        self,
        prompt: str,
        *,
        model: str | None,
        system: str | None,
        max_tokens: int | None,
        temperature: float | None,
    ) -> dict[str, Any]:
        request: dict[str, Any] = {"prompt": prompt}
        if model:
            request["model"] = model
        if system:
            request["system"] = system
        if max_tokens is not None:
            request["max_tokens"] = max_tokens
        if temperature is not None:
            request["temperature"] = temperature
        return request

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
        if images:
            raise ProviderError(
                "claude provider does not yet support frontmatter 'images:'. "
                "Use a vision-capable provider (ollama, lmstudio)."
            )
        if stop or options:
            # Claude SDK accepts stop_sequences but we'd need to thread it
            # through ClaudeHarness; out of scope for this change.
            pass
        effective_model = model or self.default_model
        harness = self._ensure_harness(effective_model)
        request = self._build_request(
            prompt,
            model=effective_model,
            system=system,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        if stream:
            return self._stream(harness, request)

        try:
            response = harness.invoke(request)
        except HarnessError as exc:
            raise ProviderError(f"claude provider failed: {exc}") from exc

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
            raise ProviderError(f"claude provider failed: {exc}") from exc
