"""Unit tests for the ClaudeProvider wrapper.

These tests exercise the ClaudeProvider's contract by injecting a fake
ClaudeHarness via the constructor — they do NOT import the anthropic SDK
or hit the network.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any

import pytest
from core.runtimes.markdown.providers import ClaudeProvider, ProviderError, ProviderResult
from harnesses.base import HarnessError


class _FakeHarness:
    """Minimal stand-in for ClaudeHarness."""

    def __init__(
        self,
        *,
        invoke_response: dict[str, Any] | None = None,
        stream_events: list[dict[str, Any]] | None = None,
        raises: Exception | None = None,
    ) -> None:
        self._invoke_response = invoke_response
        self._stream_events = stream_events or []
        self._raises = raises
        self.invoke_calls: list[Mapping[str, Any]] = []
        self.stream_calls: list[Mapping[str, Any]] = []

    def invoke(self, request: Mapping[str, Any]) -> dict[str, Any]:
        if self._raises is not None:
            raise self._raises
        self.invoke_calls.append(request)
        assert self._invoke_response is not None
        return self._invoke_response

    def stream(self, request: Mapping[str, Any]) -> Iterator[dict[str, Any]]:
        if self._raises is not None:
            raise self._raises
        self.stream_calls.append(request)
        yield from self._stream_events


def _text_response(text: str, *, model: str = "claude-sonnet-4-6") -> dict[str, Any]:
    return {
        "id": "msg_test",
        "model": model,
        "content": [{"type": "text", "text": text}],
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 1, "output_tokens": len(text)},
    }


def test_run_returns_provider_result_with_concatenated_text() -> None:
    harness = _FakeHarness(
        invoke_response={
            "model": "claude-sonnet-4-6",
            "content": [
                {"type": "text", "text": "Hello, "},
                {"type": "text", "text": "world."},
            ],
            "usage": {"output_tokens": 12},
        }
    )
    provider = ClaudeProvider(harness=harness)
    result = provider.run("test prompt")
    assert isinstance(result, ProviderResult)
    assert result.text == "Hello, world."
    assert result.model == "claude-sonnet-4-6"
    assert result.usage == {"output_tokens": 12}


def test_run_passes_model_system_and_tuning_to_harness() -> None:
    harness = _FakeHarness(invoke_response=_text_response("ok"))
    provider = ClaudeProvider(harness=harness)
    provider.run(
        "p",
        model="claude-opus-4-7",
        system="be terse",
        max_tokens=42,
        temperature=0.7,
    )
    request = harness.invoke_calls[0]
    assert request["prompt"] == "p"
    assert request["model"] == "claude-opus-4-7"
    assert request["system"] == "be terse"
    assert request["max_tokens"] == 42
    assert request["temperature"] == 0.7


def test_run_uses_default_model_when_omitted() -> None:
    harness = _FakeHarness(invoke_response=_text_response("ok"))
    provider = ClaudeProvider(harness=harness)
    provider.run("p")
    assert harness.invoke_calls[0]["model"] == ClaudeProvider.default_model


def test_run_ignores_non_text_content_blocks() -> None:
    harness = _FakeHarness(
        invoke_response={
            "model": "claude-sonnet-4-6",
            "content": [
                {"type": "tool_use", "id": "tool_1", "name": "x"},
                {"type": "text", "text": "visible"},
                {"type": "image", "source": {}},
            ],
            "usage": {},
        }
    )
    provider = ClaudeProvider(harness=harness)
    result = provider.run("p")
    assert isinstance(result, ProviderResult)
    assert result.text == "visible"


def test_run_wraps_harness_error_in_provider_error() -> None:
    harness = _FakeHarness(raises=HarnessError("ANTHROPIC_API_KEY is not set"))
    provider = ClaudeProvider(harness=harness)
    with pytest.raises(ProviderError, match="ANTHROPIC_API_KEY"):
        provider.run("p")


def test_stream_yields_only_text_deltas() -> None:
    events = [
        {"type": "message_start"},
        {"type": "content_block_start", "index": 0},
        {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "Hi "}},
        {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "there"}},
        {"type": "content_block_delta", "delta": {"type": "input_json_delta", "partial_json": "{"}},
        {"type": "content_block_stop"},
        {"type": "message_delta", "delta": {}},
        {"type": "message_stop"},
    ]
    harness = _FakeHarness(stream_events=events)
    provider = ClaudeProvider(harness=harness)
    chunks = list(provider.run("p", stream=True))  # type: ignore[arg-type]
    assert chunks == ["Hi ", "there"]


def test_stream_wraps_harness_error_in_provider_error() -> None:
    harness = _FakeHarness(raises=HarnessError("boom"))
    provider = ClaudeProvider(harness=harness)
    with pytest.raises(ProviderError, match="boom"):
        list(provider.run("p", stream=True))  # type: ignore[arg-type]
