"""Tests for lib.text.format_markdown — format_markdown_with_lmstudio and load_prompt.

The LMStudio harness is never instantiated — an injected executor stub
handles all invocations so these tests run offline.
The real prompt file at 12_prompts/text.markdown.format.task.md is loaded
by load_prompt(); it's a stable file in the repo so we use it directly.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from lib.text.format_markdown import format_markdown_with_lmstudio, load_prompt

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _StubExecutor:
    """Records calls and returns canned formatted markdown."""

    def __init__(self, content: str = "# Formatted\n\nHello.") -> None:
        self.calls: list[dict] = []
        self.content = content

    def invoke(self, payload: dict) -> dict:
        self.calls.append(payload)
        return {"choices": [{"message": {"content": self.content}}]}


# ---------------------------------------------------------------------------
# load_prompt
# ---------------------------------------------------------------------------


def test_load_prompt_returns_string() -> None:
    result = load_prompt()
    assert isinstance(result, str)
    assert len(result) > 0


def test_load_prompt_contains_template_variable() -> None:
    """The real prompt template must include {{markdown_content}}."""
    result = load_prompt()
    assert "{{markdown_content}}" in result


def test_load_prompt_raises_on_missing_file() -> None:
    with patch("lib.text.format_markdown.PROMPT_PATH", Path("/nonexistent/file.md")):
        with pytest.raises(Exception):
            load_prompt()


# ---------------------------------------------------------------------------
# format_markdown_with_lmstudio — happy path
# ---------------------------------------------------------------------------


def test_format_markdown_returns_string(tmp_path: Path) -> None:
    md_file = tmp_path / "doc.md"
    md_file.write_text("# Hello\n\nThis is a test.\n")
    executor = _StubExecutor("# Formatted\n\nHello world.")

    result = format_markdown_with_lmstudio(str(md_file), executor=executor)

    assert isinstance(result, str)
    assert result == "# Formatted\n\nHello world."


def test_format_markdown_passes_content_in_prompt(tmp_path: Path) -> None:
    md_file = tmp_path / "doc.md"
    md_file.write_text("original content\n")
    executor = _StubExecutor()

    format_markdown_with_lmstudio(str(md_file), executor=executor)

    assert len(executor.calls) == 1
    call = executor.calls[0]
    assert "original content" in call["messages"][0]["content"]


def test_format_markdown_passes_model_to_executor(tmp_path: Path) -> None:
    md_file = tmp_path / "doc.md"
    md_file.write_text("text\n")
    executor = _StubExecutor()

    format_markdown_with_lmstudio(str(md_file), model="custom-model", executor=executor)

    call = executor.calls[0]
    assert call["model"] == "custom-model"


def test_format_markdown_uses_default_model_when_not_specified(tmp_path: Path) -> None:
    md_file = tmp_path / "doc.md"
    md_file.write_text("text\n")
    executor = _StubExecutor()

    format_markdown_with_lmstudio(str(md_file), executor=executor)

    call = executor.calls[0]
    assert call["model"] == "qwen/qwen3.6-27b"


def test_format_markdown_injects_content_into_template(tmp_path: Path) -> None:
    md_file = tmp_path / "doc.md"
    md_file.write_text("my unique text\n")
    executor = _StubExecutor()

    format_markdown_with_lmstudio(str(md_file), executor=executor)

    prompt_content = executor.calls[0]["messages"][0]["content"]
    # Content is injected where {{markdown_content}} was in the template
    assert "my unique text" in prompt_content


def test_format_markdown_template_variable_replaced(tmp_path: Path) -> None:
    md_file = tmp_path / "doc.md"
    md_file.write_text("replaced content\n")
    executor = _StubExecutor()

    format_markdown_with_lmstudio(str(md_file), executor=executor)

    prompt_content = executor.calls[0]["messages"][0]["content"]
    # The placeholder itself should be gone after substitution
    assert "{{markdown_content}}" not in prompt_content


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


def test_format_markdown_raises_on_missing_file(tmp_path: Path) -> None:
    executor = _StubExecutor()
    with pytest.raises(Exception):
        format_markdown_with_lmstudio(str(tmp_path / "nonexistent.md"), executor=executor)


def test_format_markdown_propagates_executor_exception(tmp_path: Path) -> None:
    md_file = tmp_path / "doc.md"
    md_file.write_text("text\n")

    class _FailingExecutor:
        def invoke(self, payload: dict) -> dict:
            raise RuntimeError("lmstudio unreachable")

    with pytest.raises(RuntimeError, match="lmstudio unreachable"):
        format_markdown_with_lmstudio(str(md_file), executor=_FailingExecutor())


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_format_markdown_empty_file(tmp_path: Path) -> None:
    md_file = tmp_path / "empty.md"
    md_file.write_text("")
    executor = _StubExecutor("(empty doc formatted)")

    result = format_markdown_with_lmstudio(str(md_file), executor=executor)

    assert result == "(empty doc formatted)"


def test_format_markdown_messages_use_user_role(tmp_path: Path) -> None:
    md_file = tmp_path / "doc.md"
    md_file.write_text("content\n")
    executor = _StubExecutor()

    format_markdown_with_lmstudio(str(md_file), executor=executor)

    messages = executor.calls[0]["messages"]
    assert messages[0]["role"] == "user"


def test_format_markdown_executor_called_once(tmp_path: Path) -> None:
    md_file = tmp_path / "doc.md"
    md_file.write_text("text\n")
    executor = _StubExecutor()

    format_markdown_with_lmstudio(str(md_file), executor=executor)

    assert len(executor.calls) == 1
