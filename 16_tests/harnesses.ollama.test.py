"""Contract tests for harnesses.ollama.OllamaHarness.

All tests mock `urllib.request.urlopen` and `subprocess` so they run
offline without needing a running Ollama server.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from harnesses.base import HarnessError
from harnesses.ollama import OllamaHarness

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_http_response(payload: dict | str = "", status: int = 200) -> MagicMock:
    """Return a mock urllib response context manager."""
    if isinstance(payload, dict):
        body = json.dumps(payload).encode("utf-8")
    else:
        body = payload.encode("utf-8") if isinstance(payload, str) else payload

    resp = MagicMock()
    resp.status = status
    resp.read.return_value = body
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def _ndjson_response(lines: list[dict]) -> MagicMock:
    """Return a streaming response that iterates over ndjson lines."""
    raw = b"\n".join(json.dumps(ln).encode() for ln in lines)
    resp = MagicMock()
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    resp.__iter__ = lambda s: iter(raw.splitlines(keepends=True))
    return resp


def _harness() -> OllamaHarness:
    return OllamaHarness({"manage_server": False, "base_url": "http://localhost:11434"})


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------


def test_name_is_ollama() -> None:
    h = OllamaHarness()
    assert h.name == "ollama"


def test_default_model() -> None:
    h = OllamaHarness()
    assert h.model == "llama3.2"


def test_default_base_url() -> None:
    h = OllamaHarness()
    assert h.base_url == "http://localhost:11434"


def test_config_model_override() -> None:
    h = OllamaHarness({"model": "mistral"})
    assert h.model == "mistral"


def test_default_timeout() -> None:
    h = OllamaHarness()
    assert h.timeout == 120.0


def test_manage_server_default_true() -> None:
    h = OllamaHarness()
    assert h.manage_server is True


# ---------------------------------------------------------------------------
# _server_reachable
# ---------------------------------------------------------------------------


def test_server_reachable_true_when_200() -> None:
    h = _harness()
    with patch("urllib.request.urlopen", return_value=_mock_http_response("")):
        assert h._server_reachable() is True


def test_server_reachable_false_on_url_error() -> None:
    import urllib.error

    h = _harness()
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("refused")):
        assert h._server_reachable() is False


# ---------------------------------------------------------------------------
# start / stop / status
# ---------------------------------------------------------------------------


def test_start_when_reachable_sets_running() -> None:
    h = _harness()
    with patch.object(h, "_server_reachable", return_value=True):
        result = h.start()
    assert result.state == "running"
    assert "already up" in result.detail


def test_start_when_unreachable_manage_false_sets_error() -> None:
    h = _harness()
    with patch.object(h, "_server_reachable", return_value=False):
        result = h.start()
    assert result.state == "error"


def test_stop_returns_stopped() -> None:
    h = _harness()
    result = h.stop()
    assert result.state == "stopped"
    assert h._proc is None


def test_stop_kills_managed_proc() -> None:
    h = _harness()
    mock_proc = MagicMock()
    mock_proc.pid = 1234
    h._proc = mock_proc
    with patch("os.killpg"), patch("os.getpgid", return_value=1234):
        h.stop()
    assert h._proc is None


def test_status_returns_running_with_models() -> None:
    h = _harness()
    tags_payload = {"models": [{"name": "llama3.2"}, {"name": "mistral"}]}
    with patch("urllib.request.urlopen", return_value=_mock_http_response(tags_payload)):
        snap = h.status()
    assert snap.state == "running"
    assert snap.metadata["models"] == ["llama3.2", "mistral"]


def test_status_returns_stopped_on_unreachable() -> None:
    import urllib.error

    h = _harness()
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("refused")):
        snap = h.status()
    assert snap.state == "stopped"


# ---------------------------------------------------------------------------
# invoke — happy path
# ---------------------------------------------------------------------------


def test_invoke_returns_payload() -> None:
    h = _harness()
    payload = {"message": {"role": "assistant", "content": "hello"}, "done": True}
    with patch("urllib.request.urlopen", return_value=_mock_http_response(payload)):
        result = h.invoke({"prompt": "hi"})
    assert result["done"] is True
    assert result["message"]["content"] == "hello"


def test_invoke_sends_correct_model() -> None:
    h = OllamaHarness({"model": "qwen", "manage_server": False})
    payload = {"message": {"content": "ok"}, "done": True}
    mock_resp = _mock_http_response(payload)
    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_open:
        h.invoke({"prompt": "hi"})
    request_obj = mock_open.call_args[0][0]
    sent_body = json.loads(request_obj.data)
    assert sent_body["model"] == "qwen"


def test_invoke_with_messages_list() -> None:
    h = _harness()
    payload = {"message": {"content": "ok"}, "done": True}
    with patch("urllib.request.urlopen", return_value=_mock_http_response(payload)) as mock_open:
        h.invoke({"messages": [{"role": "user", "content": "hi"}]})
    sent_body = json.loads(mock_open.call_args[0][0].data)
    assert sent_body["messages"] == [{"role": "user", "content": "hi"}]


def test_invoke_passes_options() -> None:
    h = _harness()
    payload = {"message": {"content": "ok"}, "done": True}
    with patch("urllib.request.urlopen", return_value=_mock_http_response(payload)) as mock_open:
        h.invoke({"prompt": "hi", "options": {"temperature": 0.5}})
    sent_body = json.loads(mock_open.call_args[0][0].data)
    assert sent_body["options"] == {"temperature": 0.5}


# ---------------------------------------------------------------------------
# invoke — error path
# ---------------------------------------------------------------------------


def test_invoke_wraps_exception_as_harness_error() -> None:
    import urllib.error

    h = _harness()
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("timeout")):
        with pytest.raises(HarnessError, match="ollama invoke failed"):
            h.invoke({"prompt": "hi"})


# ---------------------------------------------------------------------------
# embed
# ---------------------------------------------------------------------------


def test_embed_returns_list_of_floats() -> None:
    h = _harness()
    payload = {"embedding": [0.1, 0.2, 0.3]}
    with patch("urllib.request.urlopen", return_value=_mock_http_response(payload)):
        result = h.embed("some text")
    assert result == [0.1, 0.2, 0.3]


def test_embed_uses_provided_model() -> None:
    h = _harness()
    payload = {"embedding": [1.0]}
    with patch("urllib.request.urlopen", return_value=_mock_http_response(payload)) as mock_open:
        h.embed("text", model="nomic-embed-text")
    sent_body = json.loads(mock_open.call_args[0][0].data)
    assert sent_body["model"] == "nomic-embed-text"


def test_embed_error_raises_harness_error() -> None:
    import urllib.error

    h = _harness()
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("no route")):
        with pytest.raises(HarnessError, match="ollama embed failed"):
            h.embed("some text")


# ---------------------------------------------------------------------------
# stream
# ---------------------------------------------------------------------------


def test_stream_yields_parsed_chunks() -> None:
    h = _harness()
    lines = [
        {"message": {"content": "hello"}, "done": False},
        {"message": {"content": " world"}, "done": True},
    ]
    with patch("urllib.request.urlopen", return_value=_ndjson_response(lines)):
        events = list(h.stream({"prompt": "hi"}))
    assert len(events) == 2
    assert events[0]["message"]["content"] == "hello"


def test_stream_error_raises_harness_error() -> None:
    import urllib.error

    h = _harness()
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("timeout")):
        with pytest.raises(HarnessError, match="ollama stream failed"):
            list(h.stream({"prompt": "hi"}))


# ---------------------------------------------------------------------------
# _spawn_server — error paths
# ---------------------------------------------------------------------------


def test_spawn_server_raises_when_ollama_not_on_path() -> None:
    h = OllamaHarness({"manage_server": True})
    with patch("shutil.which", return_value=None):
        with pytest.raises(HarnessError, match="`ollama` binary"):
            h._spawn_server()


# ---------------------------------------------------------------------------
# logs / health
# ---------------------------------------------------------------------------


def test_logs_tail_parameter() -> None:
    h = _harness()
    for i in range(10):
        h._record(f"line {i}")
    assert len(h.logs(tail=5)) == 5


def test_health_returns_ready_when_reachable() -> None:
    h = _harness()
    with patch("urllib.request.urlopen", return_value=_mock_http_response("")):
        snap = h.health()
    assert snap.state == "ready"


def test_health_returns_error_on_unreachable() -> None:
    import urllib.error

    h = _harness()
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("refused")):
        snap = h.health()
    assert snap.state == "error"
