"""Contract tests for harnesses.gemini.GeminiHarness.

All tests mock the `google.generativeai` SDK boundary so they run offline.
Tests are skipped when the `llm` extra is not installed.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

google_generativeai = pytest.importorskip("google.generativeai")

from harnesses.base import HarnessError, HarnessStatus  # noqa: E402
from harnesses.gemini import GeminiHarness  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_genai_module() -> MagicMock:
    genai = MagicMock()
    model_instance = MagicMock()
    genai.GenerativeModel.return_value = model_instance
    return genai, model_instance


def _mock_response(text: str = "hello") -> MagicMock:
    resp = MagicMock()
    resp.text = text
    resp.candidates = []
    resp.usage_metadata = None
    return resp


def _harness(monkeypatch: pytest.MonkeyPatch, api_key: str = "gkey-test") -> GeminiHarness:
    monkeypatch.setenv("GOOGLE_API_KEY", api_key)
    return GeminiHarness()


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------


def test_name_is_gemini() -> None:
    h = GeminiHarness()
    assert h.name == "gemini"


def test_default_model() -> None:
    h = GeminiHarness()
    assert h.model == "gemini-1.5-flash"


def test_config_model_override() -> None:
    h = GeminiHarness({"model": "gemini-pro"})
    assert h.model == "gemini-pro"


def test_default_timeout() -> None:
    h = GeminiHarness()
    assert h.timeout == 60.0


# ---------------------------------------------------------------------------
# Missing API key raises HarnessError
# ---------------------------------------------------------------------------


def test_missing_api_key_raises_harness_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    h = GeminiHarness()
    with patch("google.generativeai.configure"):
        with pytest.raises(HarnessError, match="GOOGLE_API_KEY"):
            h._ensure_model()


# ---------------------------------------------------------------------------
# start / stop / status
# ---------------------------------------------------------------------------


def test_start_sets_state_running(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    genai_mod, model_inst = _mock_genai_module()
    with (
        patch("google.generativeai.configure"),
        patch("google.generativeai.GenerativeModel", return_value=model_inst),
    ):
        result = h.start()
    assert result.state == "running"


def test_stop_clears_model_instance(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    h._model_instance = MagicMock()
    result = h.stop()
    assert h._model_instance is None
    assert result.state == "stopped"


def test_status_returns_harness_status(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    snap = h.status()
    assert isinstance(snap, HarnessStatus)
    assert snap.name == "gemini"
    assert "model=" in snap.detail


# ---------------------------------------------------------------------------
# _coerce_contents
# ---------------------------------------------------------------------------


def test_coerce_contents_passthrough_contents(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    contents = [{"role": "user", "parts": [{"text": "hi"}]}]
    result = h._coerce_contents({"contents": contents})
    assert result is contents


def test_coerce_contents_from_prompt_string(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    result = h._coerce_contents({"prompt": "hello"})
    assert result == "hello"


def test_coerce_contents_from_messages(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    msgs = [{"role": "user", "content": "hello"}]
    result = h._coerce_contents({"messages": msgs})
    assert isinstance(result, list)
    assert result[0]["role"] == "user"
    assert result[0]["parts"] == [{"text": "hello"}]


def test_coerce_contents_assistant_role_becomes_model(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    msgs = [{"role": "assistant", "content": "hi back"}]
    result = h._coerce_contents({"messages": msgs})
    assert result[0]["role"] == "model"


# ---------------------------------------------------------------------------
# invoke — happy path
# ---------------------------------------------------------------------------


def test_invoke_returns_expected_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    model_inst = MagicMock()
    model_inst.generate_content.return_value = _mock_response("hi there")
    h._model_instance = model_inst

    result = h.invoke({"prompt": "say hi"})
    assert "id" in result
    assert "model" in result
    assert "text" in result
    assert "candidates" in result
    assert "usage" in result


def test_invoke_text_content(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    model_inst = MagicMock()
    model_inst.generate_content.return_value = _mock_response("hello world")
    h._model_instance = model_inst

    result = h.invoke({"prompt": "hi"})
    assert result["text"] == "hello world"


def test_invoke_records_request_id(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    model_inst = MagicMock()
    model_inst.generate_content.return_value = _mock_response()
    h._model_instance = model_inst

    h.invoke({"prompt": "test"})
    assert len(h._request_ids) == 1


def test_invoke_with_usage_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    model_inst = MagicMock()
    resp = _mock_response()
    usage = MagicMock()
    usage.__dict__ = {"prompt_token_count": 5, "candidates_token_count": 3}
    resp.usage_metadata = usage
    model_inst.generate_content.return_value = resp
    h._model_instance = model_inst

    result = h.invoke({"prompt": "hi"})
    assert result["usage"] == {"prompt_token_count": 5, "candidates_token_count": 3}


# ---------------------------------------------------------------------------
# invoke — error path
# ---------------------------------------------------------------------------


def test_invoke_wraps_exception_as_harness_error(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    model_inst = MagicMock()
    model_inst.generate_content.side_effect = RuntimeError("quota exceeded")
    h._model_instance = model_inst

    with pytest.raises(HarnessError, match="gemini invoke failed"):
        h.invoke({"prompt": "hi"})


# ---------------------------------------------------------------------------
# stream
# ---------------------------------------------------------------------------


def test_stream_yields_chunks(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    model_inst = MagicMock()
    chunk = MagicMock()
    chunk.text = "hello"
    chunk.candidates = [MagicMock()]
    model_inst.generate_content.return_value = [chunk]
    h._model_instance = model_inst

    events = list(h.stream({"prompt": "hi"}))
    assert len(events) == 1
    assert events[0]["text"] == "hello"


def test_stream_error_raises_harness_error(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    model_inst = MagicMock()
    model_inst.generate_content.side_effect = RuntimeError("stream broke")
    h._model_instance = model_inst

    with pytest.raises(HarnessError, match="gemini stream failed"):
        list(h.stream({"prompt": "hi"}))


# ---------------------------------------------------------------------------
# logs / health
# ---------------------------------------------------------------------------


def test_logs_respects_tail(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    for i in range(6):
        h._record(f"line {i}")
    assert len(h.logs(tail=3)) == 3


def test_health_returns_ready_when_model_responds(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    model_inst = MagicMock()
    model_inst.generate_content.return_value = _mock_response()
    h._model_instance = model_inst

    snap = h.health()
    assert snap.state == "ready"


def test_health_returns_error_on_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    h = _harness(monkeypatch)
    model_inst = MagicMock()
    model_inst.generate_content.side_effect = RuntimeError("auth error")
    h._model_instance = model_inst

    snap = h.health()
    assert snap.state == "error"
    assert "auth error" in snap.detail
