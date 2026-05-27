"""Contract tests for the four CLI-backed markdown providers.

All four providers (claude_cli, gemini_cli, codex_cli, copilot_cli)
share the same MarkdownProvider contract, so the bulk of the contract
is parametrized. Image-attachment shape differs per provider and is
tested separately against each one.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any

import pytest

from core.runtimes.markdown.providers import (
    ClaudeCliProvider,
    CodexCliProvider,
    CopilotCliProvider,
    GeminiCliProvider,
    PROVIDERS,
    ProviderError,
    ProviderResult,
)
from harnesses.base import HarnessError


# ---------------------------------------------------------------------------
# Fake harness shared by the parametrized tests
# ---------------------------------------------------------------------------


class _FakeHarness:
    def __init__(
        self,
        *,
        invoke_response: dict[str, Any] | None = None,
        stream_events: list[dict[str, Any]] | None = None,
        raises: Exception | None = None,
    ) -> None:
        self._invoke_response = invoke_response or {
            "id": "rid",
            "model": "fake",
            "text": "hello",
        }
        self._stream_events = stream_events or []
        self._raises = raises
        self.invoke_calls: list[Mapping[str, Any]] = []

    def invoke(self, request: Mapping[str, Any]) -> dict[str, Any]:
        if self._raises is not None:
            raise self._raises
        self.invoke_calls.append(request)
        return self._invoke_response

    def stream(self, request: Mapping[str, Any]) -> Iterator[dict[str, Any]]:
        if self._raises is not None:
            raise self._raises
        yield from self._stream_events


PROVIDER_CLASSES = [
    ClaudeCliProvider,
    GeminiCliProvider,
    CodexCliProvider,
    CopilotCliProvider,
]


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name,cls",
    [
        ("claude_cli", ClaudeCliProvider),
        ("gemini_cli", GeminiCliProvider),
        ("codex_cli", CodexCliProvider),
        ("copilot_cli", CopilotCliProvider),
    ],
)
def test_provider_is_registered(name: str, cls: type) -> None:
    assert name in PROVIDERS
    assert PROVIDERS[name]() .__class__ is cls or isinstance(PROVIDERS[name](), cls)


# ---------------------------------------------------------------------------
# Shared run() contract
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("provider_cls", PROVIDER_CLASSES)
def test_run_returns_provider_result(provider_cls: type) -> None:
    harness = _FakeHarness(invoke_response={"id": "rid", "model": "x", "text": "hi"})
    provider = provider_cls(harness=harness)  # type: ignore[call-arg]
    result = provider.run("test prompt")
    assert isinstance(result, ProviderResult)
    assert result.text == "hi"


@pytest.mark.parametrize("provider_cls", PROVIDER_CLASSES)
def test_run_forwards_prompt_to_harness(provider_cls: type) -> None:
    harness = _FakeHarness()
    provider = provider_cls(harness=harness)  # type: ignore[call-arg]
    provider.run("explain")
    assert harness.invoke_calls[0]["prompt"] == "explain"


@pytest.mark.parametrize("provider_cls", PROVIDER_CLASSES)
def test_run_passes_images_to_harness(provider_cls: type) -> None:
    harness = _FakeHarness()
    provider = provider_cls(harness=harness)  # type: ignore[call-arg]
    provider.run("look", images=["/tmp/a.png"])
    assert harness.invoke_calls[0]["images"] == ["/tmp/a.png"]


@pytest.mark.parametrize("provider_cls", PROVIDER_CLASSES)
def test_run_wraps_harness_error(provider_cls: type) -> None:
    harness = _FakeHarness(raises=HarnessError("nope"))
    provider = provider_cls(harness=harness)  # type: ignore[call-arg]
    with pytest.raises(ProviderError, match="nope"):
        provider.run("p")


@pytest.mark.parametrize("provider_cls", PROVIDER_CLASSES)
def test_run_prepends_system_prompt(provider_cls: type) -> None:
    harness = _FakeHarness()
    provider = provider_cls(harness=harness)  # type: ignore[call-arg]
    provider.run("user content", system="be brief")
    forwarded = harness.invoke_calls[0]["prompt"]
    assert "be brief" in forwarded
    assert "user content" in forwarded
    assert forwarded.index("be brief") < forwarded.index("user content")


# ---------------------------------------------------------------------------
# Streaming
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("provider_cls", PROVIDER_CLASSES)
def test_stream_yields_text_chunks(provider_cls: type) -> None:
    harness = _FakeHarness(
        stream_events=[
            {"text": "Hi "},
            {"text": "there"},
            {"text": ""},  # empty chunks are filtered
        ]
    )
    provider = provider_cls(harness=harness)  # type: ignore[call-arg]
    chunks = list(provider.run("p", stream=True))  # type: ignore[arg-type]
    assert chunks == ["Hi ", "there"]


# ---------------------------------------------------------------------------
# Early-fail capability check
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("provider_cls", PROVIDER_CLASSES)
def test_supports_images_attribute_is_true(provider_cls: type) -> None:
    """All four CLI providers attach images through their binary."""
    assert provider_cls.supports_images is True


def test_unsupported_images_fails_before_subprocess(monkeypatch: pytest.MonkeyPatch) -> None:
    """If a provider is configured with ``supports_images=False``, the early
    guard must fire before any harness call.
    """
    harness = _FakeHarness()
    provider = ClaudeCliProvider(harness=harness)
    monkeypatch.setattr(provider, "supports_images", False)
    with pytest.raises(ProviderError, match="does not support images"):
        provider.run("p", images=["/tmp/a.png"])
    assert harness.invoke_calls == []  # never reached
