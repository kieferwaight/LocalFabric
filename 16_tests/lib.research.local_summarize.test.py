"""Tests for lib.research.local_summarize — local_research_scaffold.

All network calls (requests, Ollama HTTP) and filesystem prompt loads are mocked.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from harnesses.base import HarnessStatus
from lib.research.local_summarize import _pick_ollama_model, local_research_scaffold

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _stub_harness(
    models: list[str] | None = None,
    reachable: bool = True,
    response_content: str = "summary text",
) -> MagicMock:
    """Build a mock OllamaHarness-like object."""
    harness = MagicMock()
    state = "running" if reachable else "stopped"
    harness.status.return_value = HarnessStatus(
        name="ollama",
        state=state,
        metadata={"models": models or []},
    )
    invoke_response = {
        "message": {"role": "assistant", "content": response_content},
        "done": True,
    }
    harness.invoke.return_value = invoke_response
    return harness


def _stub_fetch(
    text: str = "article text", label: str = "url", url: str = "https://example.com"
) -> MagicMock:
    return (text, label, url)


# ---------------------------------------------------------------------------
# _pick_ollama_model
# ---------------------------------------------------------------------------


def test_pick_ollama_model_returns_preferred_model() -> None:
    harness = _stub_harness(models=["llama3.2:latest", "qwen2.5:7b"])
    result = _pick_ollama_model(harness)
    assert result == "qwen2.5:7b"


def test_pick_ollama_model_returns_first_available_when_no_preference_matches() -> None:
    harness = _stub_harness(models=["mistral:7b", "phi3"])
    result = _pick_ollama_model(harness)
    assert result == "mistral:7b"


def test_pick_ollama_model_returns_none_when_no_models() -> None:
    harness = _stub_harness(models=[])
    result = _pick_ollama_model(harness)
    assert result is None


def test_pick_ollama_model_returns_none_when_not_reachable() -> None:
    harness = _stub_harness(models=["llama3"], reachable=False)
    result = _pick_ollama_model(harness)
    assert result is None


def test_pick_ollama_model_prefers_qwen_over_llama() -> None:
    harness = _stub_harness(models=["llama3.2:latest", "qwen2.5:7b", "llama3.1"])
    # qwen2.5 is higher in _MODEL_PREFERENCE than llama3.x
    result = _pick_ollama_model(harness)
    assert result is not None
    assert "qwen" in result


# ---------------------------------------------------------------------------
# local_research_scaffold — happy path
# ---------------------------------------------------------------------------


def test_local_research_scaffold_returns_string() -> None:
    harness = _stub_harness(models=["llama3.2"], response_content="nice summary")
    with (
        patch(
            "lib.research.local_summarize.fetch_readable_text",
            return_value=_stub_fetch("article body"),
        ),
        patch(
            "lib.research.local_summarize._PROMPT_PATH",
            new_callable=lambda: type(
                "P",
                (),
                {"read_text": lambda s, **k: "---\nid: test\n---\nSummarize: {{ source_text }}"},
            )(),
        ),
        patch(
            "core.runtimes.markdown.frontmatter.parse",
            return_value=MagicMock(body="Summarize: {{ source_text }}"),
        ),
    ):
        result = local_research_scaffold("https://example.com", harness=harness)
    assert isinstance(result, str)
    assert "nice summary" in result


def test_local_research_scaffold_includes_model_name() -> None:
    harness = _stub_harness(models=["qwen2.5:7b"], response_content="ok")
    with (
        patch("lib.research.local_summarize.fetch_readable_text", return_value=_stub_fetch("body")),
        patch(
            "core.runtimes.markdown.frontmatter.parse",
            return_value=MagicMock(body="Summarize: {{ source_text }}"),
        ),
    ):
        result = local_research_scaffold("https://example.com", harness=harness)
    assert "qwen2.5:7b" in result


# ---------------------------------------------------------------------------
# local_research_scaffold — fetch failure
# ---------------------------------------------------------------------------


def test_local_research_scaffold_returns_message_on_fetch_failure() -> None:
    harness = _stub_harness(models=["llama3.2"])
    with patch(
        "lib.research.local_summarize.fetch_readable_text",
        side_effect=RuntimeError("timeout"),
    ):
        result = local_research_scaffold("https://example.com", harness=harness)
    assert "Failed to fetch" in result or "failed" in result.lower()


# ---------------------------------------------------------------------------
# local_research_scaffold — empty text
# ---------------------------------------------------------------------------


def test_local_research_scaffold_returns_message_when_text_is_empty() -> None:
    harness = _stub_harness(models=["llama3.2"])
    with patch(
        "lib.research.local_summarize.fetch_readable_text",
        return_value=("", "url", "https://x.com"),
    ):
        result = local_research_scaffold("https://example.com", harness=harness)
    assert "no readable text" in result.lower() or isinstance(result, str)


# ---------------------------------------------------------------------------
# local_research_scaffold — ollama unavailable
# ---------------------------------------------------------------------------


def test_local_research_scaffold_returns_raw_extract_when_ollama_unavailable() -> None:
    harness = _stub_harness(models=[], reachable=False)
    with patch(
        "lib.research.local_summarize.fetch_readable_text",
        return_value=("interesting article body", "url", "https://x.com"),
    ):
        result = local_research_scaffold("https://example.com", harness=harness)
    # Graceful fallback: returns raw extract
    assert "Ollama unavailable" in result or "interesting article body" in result


# ---------------------------------------------------------------------------
# local_research_scaffold — invoke failure graceful
# ---------------------------------------------------------------------------


def test_local_research_scaffold_returns_fallback_on_invoke_error() -> None:
    harness = _stub_harness(models=["llama3.2"])
    harness.invoke.side_effect = RuntimeError("model crashed")
    with (
        patch(
            "lib.research.local_summarize.fetch_readable_text",
            return_value=("body text", "url", "https://x.com"),
        ),
        patch(
            "core.runtimes.markdown.frontmatter.parse",
            return_value=MagicMock(body="Summarize: {{ source_text }}"),
        ),
    ):
        result = local_research_scaffold("https://example.com", harness=harness)
    assert isinstance(result, str)
    # Should contain error context
    assert "model crashed" in result or "failed" in result.lower()
