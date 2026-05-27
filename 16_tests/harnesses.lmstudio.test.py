"""Contract tests for harnesses.lmstudio.LMStudioHarness.

All tests mock the `openai` SDK and `urllib` boundaries so they run offline.
Tests are skipped when the `llm` extra (openai package) is not installed.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

openai = pytest.importorskip("openai")

from harnesses.base import HarnessError, HarnessStatus  # noqa: E402
from harnesses.lmstudio import LMStudioHarness  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_choice(content: str = "formatted") -> MagicMock:
    choice = MagicMock()
    choice.model_dump.return_value = {"message": {"role": "assistant", "content": content}}
    return choice


def _mock_usage() -> MagicMock:
    usage = MagicMock()
    usage.model_dump.return_value = {"prompt_tokens": 5, "completion_tokens": 3}
    return usage


def _mock_response(response_id: str = "cmpl-abc") -> MagicMock:
    resp = MagicMock()
    resp.id = response_id
    resp.model = "local-model"
    resp.choices = [_mock_choice()]
    resp.usage = _mock_usage()
    return resp


def _harness() -> LMStudioHarness:
    return LMStudioHarness(
        {"manage_server": False, "base_url": "http://localhost:1234/v1", "api_key": "lm-studio"}
    )


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------


def test_name_is_lmstudio() -> None:
    h = LMStudioHarness()
    assert h.name == "lmstudio"


def test_default_base_url() -> None:
    h = LMStudioHarness()
    assert h.base_url == "http://localhost:1234/v1"


def test_config_base_url_override() -> None:
    h = LMStudioHarness({"base_url": "http://localhost:9999/v1"})
    assert h.base_url == "http://localhost:9999/v1"


def test_default_model() -> None:
    h = LMStudioHarness()
    assert h.model == "local-model"


def test_default_timeout() -> None:
    h = LMStudioHarness()
    assert h.timeout == 120.0


def test_manage_server_default_true() -> None:
    h = LMStudioHarness()
    assert h.manage_server is True


# ---------------------------------------------------------------------------
# start — server already reachable
# ---------------------------------------------------------------------------


def test_start_when_server_reachable_sets_running() -> None:
    h = _harness()
    with patch.object(h, "_server_reachable", return_value=True):
        result = h.start()
    assert result.state == "running"


def test_start_when_server_unreachable_manage_false_sets_error() -> None:
    h = _harness()
    with patch.object(h, "_server_reachable", return_value=False):
        result = h.start()
    assert result.state == "error"


def test_start_manage_server_true_calls_spawn(monkeypatch: pytest.MonkeyPatch) -> None:
    h = LMStudioHarness({"manage_server": True})
    with (
        patch.object(h, "_server_reachable", return_value=False),
        patch.object(h, "_spawn_server") as mock_spawn,
        patch.object(h, "_ensure_client", return_value=MagicMock()),
    ):
        h.start()
    mock_spawn.assert_called_once()


# ---------------------------------------------------------------------------
# stop / status
# ---------------------------------------------------------------------------


def test_stop_clears_client() -> None:
    h = _harness()
    h._client = MagicMock()
    result = h.stop()
    assert h._client is None
    assert result.state == "stopped"


def test_status_returns_harness_status() -> None:
    h = _harness()
    snap = h.status()
    assert isinstance(snap, HarnessStatus)
    assert snap.name == "lmstudio"
    assert "base_url=" in snap.detail


# ---------------------------------------------------------------------------
# _server_reachable
# ---------------------------------------------------------------------------


def test_server_reachable_returns_true_on_200() -> None:
    h = _harness()
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    with patch("urllib.request.urlopen", return_value=mock_resp):
        assert h._server_reachable() is True


def test_server_reachable_returns_false_on_connection_error() -> None:
    import urllib.error

    h = _harness()
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("refused")):
        assert h._server_reachable() is False


# ---------------------------------------------------------------------------
# invoke — happy path
# ---------------------------------------------------------------------------


def test_invoke_returns_expected_keys() -> None:
    h = _harness()
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _mock_response()
    h._client = mock_client

    result = h.invoke({"prompt": "format this"})
    assert "id" in result
    assert "model" in result
    assert "choices" in result
    assert "usage" in result


def test_invoke_with_messages_list() -> None:
    h = _harness()
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _mock_response()
    h._client = mock_client

    msgs = [{"role": "user", "content": "format this markdown"}]
    h.invoke({"messages": msgs})
    call_kwargs = mock_client.chat.completions.create.call_args[1]
    assert call_kwargs["messages"] == msgs


def test_invoke_records_request_id() -> None:
    h = _harness()
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _mock_response("rid-99")
    h._client = mock_client

    h.invoke({"prompt": "test"})
    assert "rid-99" in h._request_ids


# ---------------------------------------------------------------------------
# invoke — error path
# ---------------------------------------------------------------------------


def test_invoke_wraps_exception_as_harness_error() -> None:
    h = _harness()
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = RuntimeError("timeout")
    h._client = mock_client

    with pytest.raises(HarnessError, match="lmstudio invoke failed"):
        h.invoke({"prompt": "hi"})


# ---------------------------------------------------------------------------
# stream
# ---------------------------------------------------------------------------


def test_stream_yields_chunks() -> None:
    h = _harness()
    chunk = MagicMock()
    chunk.model_dump.return_value = {"choices": [{"delta": {"content": "x"}}]}
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = [chunk]
    h._client = mock_client

    events = list(h.stream({"prompt": "hi"}))
    assert len(events) == 1


def test_stream_error_raises_harness_error() -> None:
    h = _harness()
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = RuntimeError("connection lost")
    h._client = mock_client

    with pytest.raises(HarnessError, match="lmstudio stream failed"):
        list(h.stream({"prompt": "hi"}))


# ---------------------------------------------------------------------------
# _spawn_server — error paths
# ---------------------------------------------------------------------------


def test_spawn_server_raises_when_lms_not_on_path() -> None:
    h = LMStudioHarness({"manage_server": True})
    with patch("shutil.which", return_value=None):
        with pytest.raises(HarnessError, match="`lms` binary"):
            h._spawn_server()


def test_spawn_server_raises_on_called_process_error() -> None:
    import subprocess

    h = LMStudioHarness({"manage_server": True})
    exc = subprocess.CalledProcessError(1, ["lms", "server", "start"], stderr="failed")
    with (
        patch("shutil.which", return_value="/usr/local/bin/lms"),
        patch("subprocess.run", side_effect=exc),
    ):
        with pytest.raises(HarnessError, match="lms server start"):
            h._spawn_server()


# ---------------------------------------------------------------------------
# logs / health
# ---------------------------------------------------------------------------


def test_logs_tail_parameter() -> None:
    h = _harness()
    for i in range(8):
        h._record(f"line {i}")
    assert len(h.logs(tail=4)) == 4


def test_health_returns_ready_when_models_reachable() -> None:
    h = _harness()
    mock_client = MagicMock()
    mock_client.models.list.return_value = []
    h._client = mock_client

    snap = h.health()
    assert snap.state == "ready"


def test_health_returns_error_on_exception() -> None:
    h = _harness()
    mock_client = MagicMock()
    mock_client.models.list.side_effect = RuntimeError("refused")
    h._client = mock_client

    snap = h.health()
    assert snap.state == "error"
