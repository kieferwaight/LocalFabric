"""Unit tests for the markdown harness fence parser."""

from __future__ import annotations

import pytest
from core.runtimes.markdown.fences import _FenceError, parse


def test_bare_fence_with_language() -> None:
    body = "intro\n```bash\necho hi\n```\n"
    fences = parse(body)
    assert len(fences) == 1
    fence = fences[0]
    assert fence.language == "bash"
    assert fence.attributes == {}
    assert fence.content == "echo hi\n"
    assert fence.start_line == 2


def test_fence_with_attributes() -> None:
    body = "```python {id: greet, description: hi}\nprint(1)\n```\n"
    fences = parse(body)
    assert fences[0].language == "python"
    assert fences[0].attributes == {"id": "greet", "description": "hi"}
    assert fences[0].content == "print(1)\n"


def test_fence_without_language_is_extracted() -> None:
    body = "```\necho noop\n```\n"
    fences = parse(body)
    assert len(fences) == 1
    assert fences[0].language == ""
    assert fences[0].content == "echo noop\n"


def test_indented_fence_strips_matching_indent() -> None:
    body = (
        "- list item:\n"
        "  ```python\n"
        "  print('hi')\n"
        "  ```\n"
    )
    fences = parse(body)
    assert len(fences) == 1
    assert fences[0].language == "python"
    assert fences[0].content == "print('hi')\n"


def test_indented_fence_preserves_extra_indent() -> None:
    body = (
        "  ```python\n"
        "  def f():\n"
        "      return 1\n"
        "  ```\n"
    )
    fences = parse(body)
    assert fences[0].content == "def f():\n    return 1\n"


def test_unclosed_fence_raises() -> None:
    body = "```python\nprint(1)\n"
    with pytest.raises(_FenceError, match="never closed"):
        parse(body)


def test_malformed_attribute_block_reports_line() -> None:
    body = "intro\n```python {id: : bad}\n```\n"
    with pytest.raises(_FenceError, match="malformed fence attributes"):
        parse(body)


def test_attribute_block_must_end_with_close_brace() -> None:
    body = "```python {id: greet\nprint(1)\n```\n"
    with pytest.raises(_FenceError, match="must end with"):
        parse(body)


def test_empty_fence_body() -> None:
    body = "```bash\n```\n"
    fences = parse(body)
    assert fences[0].content == ""
    assert fences[0].language == "bash"


def test_first_close_terminates_block() -> None:
    body = "```bash\nfirst line\n```\nmiddle\n```sh\nlast\n```\n"
    fences = parse(body)
    assert [f.language for f in fences] == ["bash", "sh"]
    assert fences[0].content == "first line\n"
    assert fences[1].content == "last\n"


def test_body_start_line_offsets_line_numbers() -> None:
    body = "first body line\n```bash\necho hi\n```\n"
    fences = parse(body, body_start_line=10)
    # The opening fence is the second body line, so start_line is 10 + 1.
    assert fences[0].start_line == 11


def test_language_token_normalized_to_lowercase() -> None:
    body = "```Python\nprint(1)\n```\n"
    fences = parse(body)
    assert fences[0].language == "python"
