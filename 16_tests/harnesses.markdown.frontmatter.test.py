"""Unit tests for the markdown harness frontmatter parser."""

from __future__ import annotations

import pytest
from core.runtimes.markdown.frontmatter import _FrontmatterError, parse


def test_parses_valid_frontmatter_and_body() -> None:
    source = "---\nid: x\ntitle: Hello\n---\nbody line 1\nbody line 2\n"
    result = parse(source)
    assert result.metadata == {"id": "x", "title": "Hello"}
    assert result.body == "body line 1\nbody line 2\n"
    assert result.body_start_line == 5


def test_missing_opening_delimiter() -> None:
    with pytest.raises(_FrontmatterError, match=":1:"):
        parse("id: x\n---\nbody\n")


def test_missing_closing_delimiter() -> None:
    with pytest.raises(_FrontmatterError, match="never closed"):
        parse("---\nid: x\ntitle: no close\nbody\n")


def test_empty_frontmatter_block_is_rejected() -> None:
    with pytest.raises(_FrontmatterError, match="'id' is required"):
        parse("---\n---\nbody\n")


def test_non_string_id_rejected() -> None:
    with pytest.raises(_FrontmatterError, match="'id' is required"):
        parse("---\nid: 42\n---\nbody\n")


def test_blank_id_rejected() -> None:
    with pytest.raises(_FrontmatterError, match="'id' is required"):
        parse("---\nid: '   '\n---\nbody\n")


def test_frontmatter_not_a_mapping() -> None:
    with pytest.raises(_FrontmatterError, match="mapping"):
        parse("---\n- 1\n- 2\n---\nbody\n")


def test_crlf_line_endings_handled() -> None:
    source = "---\r\nid: x\r\n---\r\nbody\r\n"
    result = parse(source)
    assert result.metadata == {"id": "x"}
    assert result.body == "body\n"


def test_unicode_values_preserved() -> None:
    source = '---\nid: x\ndescription: "héllo — 你好"\n---\nbody\n'
    result = parse(source)
    assert result.metadata["description"] == "héllo — 你好"


def test_malformed_yaml_reports_line() -> None:
    source = "---\nid: x\n  bad: : indent:\n---\nbody\n"
    with pytest.raises(_FrontmatterError, match="malformed YAML"):
        parse(source)


def test_source_path_appears_in_errors() -> None:
    with pytest.raises(_FrontmatterError, match="my/file.md"):
        parse("no opener\n", source_path="my/file.md")
