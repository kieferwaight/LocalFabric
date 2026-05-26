"""Unit tests for the markdown compiler."""

from __future__ import annotations

import logging

import pytest
from harnesses.markdown.compiler import MarkdownCompileError, compile_text


def test_minimal_file_compiles() -> None:
    source = (
        "---\n"
        "id: x.y\n"
        "---\n"
        "# Hi\n"
        "\n"
        "```bash {id: greet}\n"
        "echo hello\n"
        "```\n"
    )
    result = compile_text(source)
    assert result["id"] == "x.y"
    assert result["run"] == [{"bash": "echo hello\n"}]
    assert "# Hi" in result["variables"]["body"]
    # H1 fallback for title.
    assert result["title"] == "Hi"


def test_frontmatter_extends_and_mixins_pass_through() -> None:
    source = (
        "---\n"
        "id: a.b\n"
        "extends: stdlib.base\n"
        "mixins: [m.one, m.two]\n"
        "---\n"
        "body\n"
    )
    result = compile_text(source)
    assert result["extends"] == "stdlib.base"
    assert result["mixins"] == ["m.one", "m.two"]


def test_body_variable_bound_to_full_body() -> None:
    source = (
        "---\n"
        "id: x\n"
        "---\n"
        "first body line\n"
        "```bash\n"
        "echo hi\n"
        "```\n"
        "trailing line\n"
    )
    result = compile_text(source)
    body = result["variables"]["body"]
    assert "first body line" in body
    assert "```bash" in body
    assert "trailing line" in body


def test_author_declared_body_wins() -> None:
    source = (
        "---\n"
        "id: x\n"
        "variables:\n"
        "  body: \"explicit\"\n"
        "---\n"
        "implicit body\n"
    )
    result = compile_text(source)
    assert result["variables"]["body"] == "explicit"


def test_duplicate_block_ids_rejected() -> None:
    source = (
        "---\nid: x\n---\n"
        "```bash {id: dup}\necho a\n```\n"
        "```bash {id: dup}\necho b\n```\n"
    )
    with pytest.raises(MarkdownCompileError, match="duplicate block id"):
        compile_text(source)


def test_skip_drops_block_from_run() -> None:
    source = (
        "---\nid: x\n---\n"
        "```bash {id: keep}\necho keep\n```\n"
        "```bash {id: skipped, skip: true}\necho drop\n```\n"
        "```bash {id: also-keep}\necho more\n```\n"
    )
    result = compile_text(source)
    assert result["run"] == [
        {"bash": "echo keep\n"},
        {"bash": "echo more\n"},
    ]


def test_skipped_block_id_still_counted_for_uniqueness() -> None:
    source = (
        "---\nid: x\n---\n"
        "```bash {id: same, skip: true}\n```\n"
        "```bash {id: same}\necho hi\n```\n"
    )
    with pytest.raises(MarkdownCompileError, match="duplicate block id"):
        compile_text(source)


def test_unknown_languages_logged_and_dropped(caplog: pytest.LogCaptureFixture) -> None:
    source = (
        "---\nid: x\n---\n"
        "```ollama\nprompt\n```\n"
        "```bash\necho ok\n```\n"
    )
    with caplog.at_level(logging.WARNING, logger="harnesses.markdown"):
        result = compile_text(source, source_path="t.md")
    assert result["run"] == [{"bash": "echo ok\n"}]
    assert any("ollama" in rec.message for rec in caplog.records)


def test_bare_fence_without_language_is_skipped() -> None:
    source = (
        "---\nid: x\n---\n"
        "```\nnot runnable\n```\n"
        "```bash\necho runnable\n```\n"
    )
    result = compile_text(source)
    assert result["run"] == [{"bash": "echo runnable\n"}]


def test_run_block_order_matches_source() -> None:
    source = (
        "---\nid: x\n---\n"
        "```bash {id: a}\necho 1\n```\n"
        "```python {id: b}\nprint(2)\n```\n"
        "```js {id: c}\nconsole.log(3)\n```\n"
    )
    result = compile_text(source)
    assert [next(iter(b)) for b in result["run"]] == ["bash", "python", "js"]


def test_working_dir_attribute_preserved_in_metadata() -> None:
    source = (
        "---\nid: x\n---\n"
        "```bash {id: a, working_dir: /tmp}\necho hi\n```\n"
    )
    result = compile_text(source)
    block = result["run"][0]
    assert block["bash"] == "echo hi\n"
    assert block["_markdown_attributes"] == {"working_dir": "/tmp"}


def test_language_aliases_map_correctly() -> None:
    source = (
        "---\nid: x\n---\n"
        "```sh\necho 1\n```\n"
        "```py\nprint(2)\n```\n"
        "```javascript\nconsole.log(3)\n```\n"
        "```node\nconsole.log(4)\n```\n"
    )
    result = compile_text(source)
    keys = [next(iter(b)) for b in result["run"]]
    assert keys == ["sh", "python", "js", "js"]


def test_missing_frontmatter_raises_compile_error() -> None:
    with pytest.raises(MarkdownCompileError):
        compile_text("# just markdown\n")


def test_inputs_passthrough_keeps_constraint_shape() -> None:
    source = (
        "---\n"
        "id: x\n"
        "inputs:\n"
        "  name:\n"
        "    type: string\n"
        "    required: true\n"
        "---\n"
        "body\n"
    )
    result = compile_text(source)
    assert result["inputs"] == {"name": {"type": "string", "required": True}}
