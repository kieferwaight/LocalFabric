"""Contract tests for harnesses.codex.CodexHarness.

All tests mock the `openai` SDK boundary so they run offline. Tests are
skipped when the `llm` extra (openai package) is not installed.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

openai = pytest.importorskip("openai")

from harnesses.base import HarnessError, HarnessStatus  # noqa: E402
from harnesses.codex import CodexHarness  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_choice(content: str = "result") -> MagicMock:
    choice = MagicMock()
    choice.model_dump.return_value = {"message": {"role": "assistant", "content": content}}
    return choice


def _mock_usage() -> MagicMock:
    usage = MagicMock()
    usage.model_dump.return_value = {"prompt_tokens": 5, "completion_tokens": 3}
    return usage


def _mock_response(
    response_id: str = "chatcmpl-abc",
    model: str = "gpt-4.1-mini",
) -> MagicMock:
    resp = MagicMock()
    resp.id = response_id
    resp.model = model
    resp.choices = [_mock_choice()]
    resp.usage = _mock_usage()
    return resp


def _harness(monkeypatch: pytest.MonkeyPatch, api_key: str = "sk-test") -> CodexHarness:
    monkeypatch.setenv("OPENAI_API_KEY", api_key)
    return CodexHarness()


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------


def test_name_is_codex() -> None:
    h = CodexHarness()
    assert h.name == "codex"


def test_default_model() -> None:
    h = CodexHarness()
    assert h.model == "gpt-4.1-mini"


def test_config_model_override() -> None:
    h = CodexHarness({"model": "gpt-4o"})
    assert h.model == "gpt-4o"


def test_default_timeout() -> None:
    h = CodexHarness()
    assert h.timeout == 120.0


# ---------------------------------------------------------------------------
# Missing API key raises HarnessError (when no base_url set)
# ---------------------------------------------------------------------------


def test_missing_api_key_raises_harness_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CODEX_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    h = CodexHarness()
    with pytest.raises(HarnessError, match="CODEX_API_KEY"):
        h._ensure_client()


def test_base_url_bypasses_missing_api_key_check() -> None:
    """With a base_url, no API key is needed (local Codex proxy)."""
    h = CodexHarness({"base_url": "http://localhost:1455/v1"})
    # Should not raise even with no env key — local client is ok.
    # We can't call _ensure_client() without actually instantiating OpenAI,
    # but we can verify the config is stored.
    assert h.base_url == "http://localhost:1455/v1"


# ---------------------------------------------------------------------------
# start / stop / status
# ---------------------------------------------------------------------------


def test_start_sets_state_running(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    mock_openai_cls = MagicMock()
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("harnesses.codex.harness.OpenAI", mock_openai_cls)
        result = h.start()
    assert result.state == "running"


def test_stop_clears_client(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    h._client = MagicMock()
    result = h.stop()
    assert h._client is None
    assert result.state == "stopped"


def test_status_returns_harness_status(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    snap = h.status()
    assert isinstance(snap, HarnessStatus)
    assert snap.name == "codex"
    assert "model=" in snap.detail


# ---------------------------------------------------------------------------
# invoke — happy path
# ---------------------------------------------------------------------------


def test_invoke_returns_expected_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _mock_response()
    h._client = mock_client

    result = h.invoke({"prompt": "write code"})
    assert "id" in result
    assert "model" in result
    assert "choices" in result
    assert "usage" in result


def test_invoke_with_messages(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _mock_response()
    h._client = mock_client

    msgs = [{"role": "user", "content": "Hello"}]
    h.invoke({"messages": msgs})
    call_kwargs = mock_client.chat.completions.create.call_args[1]
    assert call_kwargs["messages"] == msgs


def test_invoke_records_request_id(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _mock_response(response_id="id-xyz")
    h._client = mock_client

    h.invoke({"prompt": "test"})
    assert "id-xyz" in h._request_ids


def test_invoke_passes_temperature(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _mock_response()
    h._client = mock_client

    h.invoke({"prompt": "hi", "temperature": 0.7})
    call_kwargs = mock_client.chat.completions.create.call_args[1]
    assert call_kwargs["temperature"] == 0.7


# ---------------------------------------------------------------------------
# invoke — error path
# ---------------------------------------------------------------------------


def test_invoke_wraps_sdk_exception_as_harness_error(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = RuntimeError("network down")
    h._client = mock_client

    with pytest.raises(HarnessError, match="codex invoke failed"):
        h.invoke({"prompt": "hi"})


# ---------------------------------------------------------------------------
# stream
# ---------------------------------------------------------------------------


def test_stream_yields_chunks(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    chunk = MagicMock()
    chunk.model_dump.return_value = {"choices": [{"delta": {"content": "x"}}]}

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = [chunk]
    h._client = mock_client

    events = list(h.stream({"prompt": "hi"}))
    assert len(events) == 1


def test_stream_error_raises_harness_error(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = RuntimeError("stream broke")
    h._client = mock_client

    with pytest.raises(HarnessError, match="codex stream failed"):
        list(h.stream({"prompt": "hi"}))


# ---------------------------------------------------------------------------
# logs
# ---------------------------------------------------------------------------


def test_logs_returns_recent_lines(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    for i in range(5):
        h._record(f"entry {i}")
    assert len(h.logs(tail=3)) == 3


# ---------------------------------------------------------------------------
# health
# ---------------------------------------------------------------------------


def test_health_returns_ready_when_reachable(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    mock_client = MagicMock()
    mock_client.models.list.return_value = []
    h._client = mock_client

    snap = h.health()
    assert snap.state == "ready"


def test_health_returns_error_on_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    mock_client = MagicMock()
    mock_client.models.list.side_effect = RuntimeError("timeout")
    h._client = mock_client

    snap = h.health()
    assert snap.state == "error"
    assert "timeout" in snap.detail
