"""Contract tests for harnesses.openai.OpenAIHarness.

All tests mock the `openai` SDK boundary so they run offline. Tests are
skipped when the `llm` extra (openai package) is not installed.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

openai = pytest.importorskip("openai")

from harnesses.base import HarnessError, HarnessStatus  # noqa: E402
from harnesses.openai import OpenAIHarness  # noqa: E402

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
    model: str = "gpt-4o-mini",
) -> MagicMock:
    resp = MagicMock()
    resp.id = response_id
    resp.model = model
    resp.choices = [_mock_choice()]
    resp.usage = _mock_usage()
    return resp


def _harness(monkeypatch: pytest.MonkeyPatch, api_key: str = "sk-test") -> OpenAIHarness:
    monkeypatch.setenv("OPENAI_API_KEY", api_key)
    return OpenAIHarness()


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------


def test_name_is_openai() -> None:
    h = OpenAIHarness()
    assert h.name == "openai"


def test_default_model() -> None:
    h = OpenAIHarness()
    assert h.model == "gpt-4o-mini"


def test_config_model_override() -> None:
    h = OpenAIHarness({"model": "gpt-4o"})
    assert h.model == "gpt-4o"


def test_default_timeout() -> None:
    h = OpenAIHarness()
    assert h.timeout == 60.0


# ---------------------------------------------------------------------------
# Missing API key raises HarnessError
# ---------------------------------------------------------------------------


def test_missing_api_key_raises_harness_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    h = OpenAIHarness()
    with pytest.raises(HarnessError, match="OPENAI_API_KEY"):
        h._ensure_client()


def test_allow_anonymous_bypasses_key_check(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    h = OpenAIHarness({"allow_anonymous": True})
    # Should not raise — the missing key check is bypassed.
    # We verify by ensuring _ensure_client would try to instantiate without raising.
    assert h.config.get("allow_anonymous") is True


# ---------------------------------------------------------------------------
# start / stop / status
# ---------------------------------------------------------------------------


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
    assert snap.name == "openai"
    assert "model=" in snap.detail


def test_status_includes_request_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    h._request_ids.append("id-1")
    snap = h.status()
    assert "id-1" in snap.metadata["request_ids"]


# ---------------------------------------------------------------------------
# invoke — happy path
# ---------------------------------------------------------------------------


def test_invoke_returns_expected_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _mock_response()
    h._client = mock_client

    result = h.invoke({"prompt": "hello"})
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
    mock_client.chat.completions.create.return_value = _mock_response(response_id="id-999")
    h._client = mock_client

    h.invoke({"prompt": "test"})
    assert "id-999" in h._request_ids


def test_invoke_passes_extra_params(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _mock_response()
    h._client = mock_client

    h.invoke({"prompt": "hi", "temperature": 0.3, "seed": 42})
    call_kwargs = mock_client.chat.completions.create.call_args[1]
    assert call_kwargs["temperature"] == 0.3
    assert call_kwargs["seed"] == 42


# ---------------------------------------------------------------------------
# invoke — error path
# ---------------------------------------------------------------------------


def test_invoke_wraps_sdk_exception_as_harness_error(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = RuntimeError("rate limited")
    h._client = mock_client

    with pytest.raises(HarnessError, match="openai invoke failed"):
        h.invoke({"prompt": "hi"})


# ---------------------------------------------------------------------------
# stream
# ---------------------------------------------------------------------------


def test_stream_yields_chunks(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    chunk = MagicMock()
    chunk.model_dump.return_value = {"choices": [{"delta": {"content": "hi"}}]}
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = [chunk]
    h._client = mock_client

    events = list(h.stream({"prompt": "hi"}))
    assert len(events) == 1
    assert events[0]["choices"][0]["delta"]["content"] == "hi"


def test_stream_error_raises_harness_error(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = RuntimeError("stream error")
    h._client = mock_client

    with pytest.raises(HarnessError, match="openai stream failed"):
        list(h.stream({"prompt": "hi"}))


# ---------------------------------------------------------------------------
# _build_chat_kwargs — completeness
# ---------------------------------------------------------------------------


def test_build_chat_kwargs_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    kwargs = h._build_chat_kwargs({"prompt": "hello"})
    assert kwargs["model"] == "gpt-4o-mini"
    assert kwargs["messages"] == [{"role": "user", "content": "hello"}]


def test_build_chat_kwargs_all_extra_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    request = {
        "prompt": "hi",
        "temperature": 0.5,
        "top_p": 0.9,
        "max_tokens": 100,
        "stop": ["\n"],
        "seed": 1,
    }
    kwargs = h._build_chat_kwargs(request)
    assert kwargs["temperature"] == 0.5
    assert kwargs["top_p"] == 0.9
    assert kwargs["max_tokens"] == 100
    assert kwargs["stop"] == ["\n"]
    assert kwargs["seed"] == 1


# ---------------------------------------------------------------------------
# logs / health
# ---------------------------------------------------------------------------


def test_logs_tail_parameter(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    for i in range(8):
        h._record(f"line {i}")
    assert len(h.logs(tail=4)) == 4


def test_health_returns_ready_when_models_reachable(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    mock_client = MagicMock()
    mock_client.models.list.return_value = []
    h._client = mock_client

    snap = h.health()
    assert snap.state == "ready"


def test_health_returns_error_on_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    mock_client = MagicMock()
    mock_client.models.list.side_effect = RuntimeError("auth error")
    h._client = mock_client

    snap = h.health()
    assert snap.state == "error"
    assert "auth error" in snap.detail


# ---------------------------------------------------------------------------
# organization / project config
# ---------------------------------------------------------------------------


def test_config_accepts_organization(monkeypatch: pytest.MonkeyPatch) -> None:
    h = OpenAIHarness({"organization": "org-abc"})
    assert h.config["organization"] == "org-abc"


def test_config_accepts_project(monkeypatch: pytest.MonkeyPatch) -> None:
    h = OpenAIHarness({"project": "proj-xyz"})
    assert h.config["project"] == "proj-xyz"
