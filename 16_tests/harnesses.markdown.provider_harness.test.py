"""Provider-style dispatch tests for MarkdownHarness.

These tests inject a stub provider via ``MarkdownHarness(provider_overrides=...)``
so they never touch the Anthropic SDK or hit the network. A separate test
verifies that the real ``ClaudeProvider`` raises a clear error when
``ANTHROPIC_API_KEY`` is missing.
"""

from __future__ import annotations

import io
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from harnesses.markdown import (
    ClaudeProvider,
    MarkdownHarness,
    MarkdownProvider,
    ProviderError,
    ProviderResult,
)
from harnesses.markdown.providers.base import MarkdownProvider as BaseProvider

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class _StubProvider(BaseProvider):
    """Test double — records every call and returns a canned response."""

    name = "claude"
    default_model = "stub-model"

    def __init__(self, *, response_text: str = "[stub-response]") -> None:
        self.response_text = response_text
        self.calls: list[dict[str, Any]] = []

    def run(
        self,
        prompt: str,
        *,
        model: str | None = None,
        system: str | None = None,
        stream: bool = False,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> ProviderResult | Iterator[str]:
        self.calls.append(
            {
                "prompt": prompt,
                "model": model,
                "system": system,
                "stream": stream,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
        )
        if stream:
            return iter([self.response_text])
        return ProviderResult(
            text=self.response_text,
            model=model or self.default_model,
            usage={"input_tokens": 1, "output_tokens": len(self.response_text)},
        )


def _harness(provider: MarkdownProvider, *, stdout: io.StringIO | None = None) -> MarkdownHarness:
    return MarkdownHarness(provider_overrides={"claude": provider}, stdout=stdout)


def test_execute_returns_provider_result_with_rendered_prompt() -> None:
    provider = _StubProvider()
    harness = _harness(provider)
    result = harness.execute(
        FIXTURES / "provider_claude.md",
        arguments={"input": "def add(a, b): return a + b"},
    )
    assert isinstance(result, ProviderResult)
    assert result.text == "[stub-response]"
    assert provider.calls[0]["model"] == "claude-sonnet-4-6"
    # The {{ input }} token must be rendered into the prompt.
    assert "def add(a, b): return a + b" in provider.calls[0]["prompt"]
    assert provider.calls[0]["system"] is None
    assert provider.calls[0]["stream"] is False


def test_execute_passes_system_and_tuning() -> None:
    provider = _StubProvider()
    result = _harness(provider).execute(FIXTURES / "provider_claude_system.md")
    assert isinstance(result, ProviderResult)
    call = provider.calls[0]
    assert call["system"] == "You are a terse assistant. Reply in 5 words or fewer."
    assert call["max_tokens"] == 64
    assert call["temperature"] == 0.2
    assert call["stream"] is False
    assert call["model"] == "claude-sonnet-4-6"


def test_missing_required_input_raises_value_error() -> None:
    provider = _StubProvider()
    harness = _harness(provider)
    with pytest.raises(ValueError, match="Missing required input"):
        harness.execute(FIXTURES / "provider_claude.md", arguments={})


def test_execute_streams_to_stdout_when_requested() -> None:
    provider = _StubProvider(response_text="hello world")
    out = io.StringIO()
    harness = _harness(provider, stdout=out)
    result = harness.execute(
        FIXTURES / "provider_claude_stream.md",
        arguments={"topic": "tides"},
    )
    # Streaming returns an iterator; draining it triggers stdout writes.
    chunks = list(result)  # type: ignore[arg-type]
    assert chunks == ["hello world"]
    assert out.getvalue() == "hello world"
    assert provider.calls[0]["stream"] is True
    # The {{ topic }} token must be rendered.
    assert "tides" in provider.calls[0]["prompt"]


def test_register_provider_file_does_not_touch_yaml_registry() -> None:
    provider = _StubProvider()
    harness = _harness(provider)
    def_id = harness.register(FIXTURES / "provider_claude_minimal.md")
    assert def_id == "tests.provider-claude-minimal"
    # Provider files are not registered with the YAML runtime; their dicts
    # have no `run:` list and would fail schema validation.
    assert def_id not in harness.runtime.registry


def test_provider_dispatch_with_minimal_frontmatter_passes_no_model() -> None:
    provider = _StubProvider(response_text="ok")
    result = _harness(provider).execute(FIXTURES / "provider_claude_minimal.md")
    assert isinstance(result, ProviderResult)
    # The compiler doesn't bake in a default; the harness forwards `None`
    # so each provider can apply its own default at call time.
    assert provider.calls[0]["model"] is None


def test_unknown_provider_name_raises_keyerror(tmp_path: Path) -> None:
    bad = tmp_path / "nope.md"
    bad.write_text(
        "---\nid: tests.unknown-provider\nprovider: not-a-real-provider\n---\nhi\n"
    )
    harness = MarkdownHarness()
    with pytest.raises(KeyError, match="Unknown markdown provider"):
        harness.execute(bad)


def test_provider_error_propagates() -> None:
    class _Failing(BaseProvider):
        name = "claude"
        def run(self, prompt: str, **_: Any) -> ProviderResult:  # type: ignore[override]
            raise ProviderError("upstream blew up")

    harness = MarkdownHarness(provider_overrides={"claude": _Failing()})
    with pytest.raises(ProviderError, match="upstream blew up"):
        harness.execute(FIXTURES / "provider_claude_minimal.md")


def test_unexpected_exception_wrapped_in_provider_error() -> None:
    class _Boom(BaseProvider):
        name = "claude"
        def run(self, prompt: str, **_: Any) -> ProviderResult:  # type: ignore[override]
            raise RuntimeError("uncaught SDK quirk")

    harness = MarkdownHarness(provider_overrides={"claude": _Boom()})
    with pytest.raises(ProviderError, match="unexpected error"):
        harness.execute(FIXTURES / "provider_claude_minimal.md")


def test_claude_provider_missing_api_key_raises_clear_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Force the env to be empty so the underlying ClaudeHarness raises.
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    provider = ClaudeProvider()
    harness = MarkdownHarness(provider_overrides={"claude": provider})
    with pytest.raises(ProviderError, match="ANTHROPIC_API_KEY"):
        harness.execute(FIXTURES / "provider_claude_minimal.md")


def test_fence_style_still_dispatches_through_yaml_runtime() -> None:
    # Regression: provider plumbing must not change fence-style behavior.
    harness = MarkdownHarness()
    scope = harness.execute(FIXTURES / "minimal.md")
    assert isinstance(scope, dict)
    assert scope["entity_id"] == "tests.minimal"
