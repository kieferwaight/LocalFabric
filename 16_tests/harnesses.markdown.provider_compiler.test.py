"""Unit tests for provider-style compilation (frontmatter ``provider:``)."""

from __future__ import annotations

import pytest
from core.runtimes.markdown.compiler import (
    PROVIDER_MARKER_KEY,
    MarkdownCompileError,
    compile_text,
)


def test_provider_style_compiles_to_marker_dict() -> None:
    source = (
        "---\n"
        "id: x.summarize\n"
        "description: Summarize code\n"
        "provider: claude\n"
        "model: claude-sonnet-4-6\n"
        "---\n"
        "You are a senior engineer.\n"
        "\n"
        "{{ input }}\n"
    )
    result = compile_text(source, source_path="t.md")
    assert PROVIDER_MARKER_KEY in result
    config = result[PROVIDER_MARKER_KEY]
    assert config["provider"] == "claude"
    assert config["model"] == "claude-sonnet-4-6"
    assert "{{ input }}" in config["prompt_template"]
    assert config["source_path"] == "t.md"
    assert result["id"] == "x.summarize"
    assert result["description"] == "Summarize code"
    # Provider-style definitions never get a `run` list.
    assert "run" not in result


def test_provider_style_without_model_omits_default() -> None:
    # The compiler does NOT bake a default model in. The provider does, at
    # call time, so swapping providers picks up sensible defaults per provider.
    source = "---\nid: x.y\nprovider: claude\n---\nhello\n"
    config = compile_text(source)[PROVIDER_MARKER_KEY]
    assert "model" not in config


def test_provider_style_preserves_inputs() -> None:
    source = (
        "---\n"
        "id: x.y\n"
        "provider: claude\n"
        "inputs:\n"
        "  input:\n"
        "    type: string\n"
        "    required: true\n"
        "---\n"
        "{{ input }}\n"
    )
    result = compile_text(source)
    assert result["inputs"] == {"input": {"type": "string", "required": True}}


def test_provider_style_passes_system_and_tuning() -> None:
    source = (
        "---\n"
        "id: x.y\n"
        "provider: claude\n"
        "system: Be terse.\n"
        "max_tokens: 64\n"
        "temperature: 0.3\n"
        "stream: true\n"
        "---\n"
        "body\n"
    )
    config = compile_text(source)[PROVIDER_MARKER_KEY]
    assert config["system"] == "Be terse."
    assert config["max_tokens"] == 64
    assert config["temperature"] == 0.3
    assert config["stream"] is True


def test_provider_rejects_empty_provider_value() -> None:
    source = "---\nid: x\nprovider: ''\n---\nbody\n"
    with pytest.raises(MarkdownCompileError, match="provider"):
        compile_text(source)


def test_provider_rejects_non_string_model() -> None:
    source = "---\nid: x\nprovider: claude\nmodel: 5\n---\nbody\n"
    with pytest.raises(MarkdownCompileError, match="model"):
        compile_text(source)


def test_provider_rejects_non_string_system() -> None:
    source = "---\nid: x\nprovider: claude\nsystem: [a, b]\n---\nbody\n"
    with pytest.raises(MarkdownCompileError, match="system"):
        compile_text(source)


def test_provider_rejects_non_int_max_tokens() -> None:
    source = "---\nid: x\nprovider: claude\nmax_tokens: 1.5\n---\nbody\n"
    with pytest.raises(MarkdownCompileError, match="max_tokens"):
        compile_text(source)


def test_provider_rejects_non_bool_stream() -> None:
    source = "---\nid: x\nprovider: claude\nstream: yes-please\n---\nbody\n"
    with pytest.raises(MarkdownCompileError, match="stream"):
        compile_text(source)


def test_provider_rejects_fence_style_keys() -> None:
    source = "---\nid: x\nprovider: claude\nextends: stdlib.base\n---\nbody\n"
    with pytest.raises(MarkdownCompileError, match="extends"):
        compile_text(source)


def test_fence_style_unchanged_when_provider_absent() -> None:
    source = "---\nid: x\n---\n```bash {id: a}\necho hi\n```\n"
    result = compile_text(source)
    assert PROVIDER_MARKER_KEY not in result
    assert result["run"] == [{"bash": "echo hi\n"}]
