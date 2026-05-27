"""Contract tests for harnesses.claude.ClaudeHarness.

All tests mock the SDK at the `anthropic` boundary so they run offline.
The `pytest.importorskip("anthropic")` guards skip the module gracefully
when the `llm` extra is not installed (e.g. CI's `dev`-only sync).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

anthropic = pytest.importorskip("anthropic")

from harnesses.base import HarnessError, HarnessStatus  # noqa: E402
from harnesses.claude import ClaudeHarness  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_content_block(text: str = "hello") -> MagicMock:
    block = MagicMock()
    block.model_dump.return_value = {"type": "text", "text": text}
    return block


def _mock_usage() -> MagicMock:
    usage = MagicMock()
    usage.model_dump.return_value = {"input_tokens": 5, "output_tokens": 3}
    return usage


def _mock_response(
    response_id: str = "msg_abc",
    model: str = "claude-sonnet-4-5",
    text: str = "hello",
) -> MagicMock:
    resp = MagicMock()
    resp.id = response_id
    resp.model = model
    resp.content = [_mock_content_block(text)]
    resp.stop_reason = "end_turn"
    resp.usage = _mock_usage()
    return resp


def _harness(monkeypatch: pytest.MonkeyPatch, api_key: str = "test-key") -> ClaudeHarness:
    monkeypatch.setenv("ANTHROPIC_API_KEY", api_key)
    return ClaudeHarness()


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------


def test_name_is_claude() -> None:
    h = ClaudeHarness()
    assert h.name == "claude"


def test_default_model() -> None:
    h = ClaudeHarness()
    assert h.model == "claude-sonnet-4-5"


def test_config_model_override() -> None:
    h = ClaudeHarness({"model": "claude-opus-4-0"})
    assert h.model == "claude-opus-4-0"


def test_default_max_tokens() -> None:
    h = ClaudeHarness()
    assert h.max_tokens == 1024


def test_default_timeout() -> None:
    h = ClaudeHarness()
    assert h.timeout == 60.0


# ---------------------------------------------------------------------------
# Missing API key raises HarnessError
# ---------------------------------------------------------------------------


def test_missing_api_key_raises_harness_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    h = ClaudeHarness()
    with pytest.raises(HarnessError, match="ANTHROPIC_API_KEY"):
        h._ensure_client()


# ---------------------------------------------------------------------------
# start / stop / status
# ---------------------------------------------------------------------------


def test_start_sets_state_running(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    with patch("anthropic.Anthropic"):
        result = h.start()
    assert result.state == "running"
    assert h._state == "running"


def test_stop_sets_state_stopped(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    with patch("anthropic.Anthropic"):
        h.start()
    result = h.stop()
    assert result.state == "stopped"
    assert h._client is None


def test_status_returns_harness_status(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    snap = h.status()
    assert isinstance(snap, HarnessStatus)
    assert snap.name == "claude"
    assert "model=" in snap.detail


# ---------------------------------------------------------------------------
# invoke — happy path
# ---------------------------------------------------------------------------


def test_invoke_returns_expected_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _mock_response()
    h._client = mock_client

    result = h.invoke({"prompt": "say hi"})

    assert "id" in result
    assert "model" in result
    assert "content" in result
    assert "stop_reason" in result
    assert "usage" in result


def test_invoke_with_prompt_string(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    mock_client = MagicMock()
    response = _mock_response(response_id="rid1")
    mock_client.messages.create.return_value = response
    h._client = mock_client

    result = h.invoke({"prompt": "hello"})
    assert result["id"] == "rid1"


def test_invoke_with_messages_list(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _mock_response()
    h._client = mock_client

    result = h.invoke({"messages": [{"role": "user", "content": "hi"}]})
    assert isinstance(result, dict)
    call_kwargs = mock_client.messages.create.call_args[1]
    assert call_kwargs["messages"] == [{"role": "user", "content": "hi"}]


def test_invoke_passes_system_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _mock_response()
    h._client = mock_client

    h.invoke({"prompt": "hi", "system": "You are helpful"})
    call_kwargs = mock_client.messages.create.call_args[1]
    assert call_kwargs["system"] == "You are helpful"


def test_invoke_records_request_id(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _mock_response(response_id="req-xyz")
    h._client = mock_client

    h.invoke({"prompt": "test"})
    assert "req-xyz" in h._request_ids


# ---------------------------------------------------------------------------
# invoke — error path
# ---------------------------------------------------------------------------


def test_invoke_wraps_sdk_exception_as_harness_error(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = RuntimeError("network failure")
    h._client = mock_client

    with pytest.raises(HarnessError, match="claude invoke failed"):
        h.invoke({"prompt": "hi"})


# ---------------------------------------------------------------------------
# stream — happy path
# ---------------------------------------------------------------------------


def test_stream_yields_events(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)

    mock_event = MagicMock()
    mock_event.model_dump.return_value = {"type": "content_block_delta", "delta": "x"}

    mock_final = MagicMock()
    mock_final.id = "stream-id"

    mock_stream_ctx = MagicMock()
    mock_stream_ctx.__enter__.return_value = mock_stream_ctx
    mock_stream_ctx.__exit__.return_value = False
    mock_stream_ctx.__iter__.return_value = iter([mock_event])
    mock_stream_ctx.get_final_message.return_value = mock_final

    mock_client = MagicMock()
    mock_client.messages.stream.return_value = mock_stream_ctx
    h._client = mock_client

    events = list(h.stream({"prompt": "hello"}))
    assert len(events) == 1
    assert events[0]["type"] == "content_block_delta"


def test_stream_error_raises_harness_error(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)

    mock_stream_ctx = MagicMock()
    mock_stream_ctx.__enter__.side_effect = RuntimeError("stream broke")
    mock_client = MagicMock()
    mock_client.messages.stream.return_value = mock_stream_ctx
    h._client = mock_client

    with pytest.raises(HarnessError, match="claude stream failed"):
        list(h.stream({"prompt": "hi"}))


# ---------------------------------------------------------------------------
# logs
# ---------------------------------------------------------------------------


def test_logs_returns_list_of_strings(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    h._record("log line 1")
    h._record("log line 2")
    result = h.logs()
    assert isinstance(result, list)
    assert "log line 1" in result


def test_logs_tail_parameter(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    for i in range(10):
        h._record(f"line {i}")
    assert len(h.logs(tail=3)) == 3


# ---------------------------------------------------------------------------
# health
# ---------------------------------------------------------------------------


def test_health_returns_ready_when_api_reachable(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _mock_response()
    h._client = mock_client

    snap = h.health()
    assert snap.state == "ready"


def test_health_returns_error_on_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = RuntimeError("auth error")
    h._client = mock_client

    snap = h.health()
    assert snap.state == "error"
    assert "auth error" in snap.detail


# ---------------------------------------------------------------------------
# _build_messages_kwargs
# ---------------------------------------------------------------------------


def test_build_messages_kwargs_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    kwargs = h._build_messages_kwargs({"prompt": "hi"})
    assert kwargs["model"] == h.model
    assert kwargs["max_tokens"] == h.max_tokens
    assert kwargs["messages"] == [{"role": "user", "content": "hi"}]


def test_build_messages_kwargs_with_temperature(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    kwargs = h._build_messages_kwargs({"prompt": "hi", "temperature": 0.5})
    assert kwargs["temperature"] == 0.5
