"""YAML frontmatter extraction for markdown sources.

Pure parser: no I/O, no logging side effects. Operates on a string and returns
a `(metadata, body, body_start_line)` tuple. `body_start_line` is 1-indexed and
points at the first body line in the original source — useful for downstream
error messages.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import yaml


@dataclass(frozen=True)
class Frontmatter:
    metadata: dict[str, Any]
    body: str
    body_start_line: int


def parse(source: str, *, source_path: str = "<string>") -> Frontmatter:
    """Extract YAML frontmatter and return (metadata, body, body_start_line).

    Raises `_FrontmatterError` (a `ValueError` subclass) on malformed input.
    The compiler wraps these into `MarkdownCompileError` with source-path
    context, so the parser itself stays I/O-free.
    """
    # Normalize CRLF → LF before splitting so line numbers line up with what
    # an author sees in their editor.
    normalized = source.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")

    if not lines or lines[0].strip() != "---":
        raise _FrontmatterError(
            f"{source_path}:1: expected '---' on the first line to open frontmatter."
        )

    close_index: int | None = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            close_index = idx
            break
    if close_index is None:
        raise _FrontmatterError(
            f"{source_path}: frontmatter block opened on line 1 was never closed with '---'."
        )

    raw_block = "\n".join(lines[1:close_index])
    try:
        metadata = yaml.safe_load(raw_block) if raw_block.strip() else None
    except yaml.YAMLError as exc:
        # Anchor to the block start line (line 2) rather than the close, since
        # YAML's own line numbers within the block are 1-indexed from there.
        problem_mark = getattr(exc, "problem_mark", None)
        if problem_mark is not None:
            line_no = 2 + problem_mark.line
            raise _FrontmatterError(
                f"{source_path}:{line_no}: malformed YAML frontmatter: {exc}"
            ) from exc
        raise _FrontmatterError(f"{source_path}: malformed YAML frontmatter: {exc}") from exc

    if metadata is None:
        raise _FrontmatterError(
            f"{source_path}:1-{close_index + 1}: frontmatter block is empty; an 'id' is required."
        )
    if not isinstance(metadata, dict):
        raise _FrontmatterError(
            f"{source_path}:1-{close_index + 1}: frontmatter must be a YAML mapping, got "
            f"{type(metadata).__name__}."
        )

    raw_id = metadata.get("id")
    if not isinstance(raw_id, str) or not raw_id.strip():
        raise _FrontmatterError(
            f"{source_path}:1-{close_index + 1}: frontmatter 'id' is required and must be a "
            "non-empty string."
        )

    body_lines = lines[close_index + 1 :]
    body = "\n".join(body_lines)
    body_start_line = close_index + 2  # 1-indexed line after the closing '---'
    return Frontmatter(metadata=metadata, body=body, body_start_line=body_start_line)


class _FrontmatterError(ValueError):
    """Internal exception type. The compiler re-raises as MarkdownCompileError."""
