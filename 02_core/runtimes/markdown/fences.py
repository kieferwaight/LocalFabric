"""Fenced code-block parser for the markdown harness.

Recognizes triple-backtick fences with an optional language token and an
optional `{key: value, ...}` attribute mapping. The attribute mapping is
parsed as a YAML flow mapping, so strings/numbers/booleans/lists/nested
maps all work without a custom grammar.

Nested fences are *not* supported — the first matching closing line ends a
fence. This limitation is documented in the harness README.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import yaml

_FENCE_OPEN_RE = re.compile(r"^(?P<indent>[ \t]*)```(?P<info>[^\n]*)$")


@dataclass(frozen=True)
class Fence:
    language: str  # lowercased fence info word; "" if no language token
    attributes: dict[str, Any] = field(default_factory=dict)
    content: str = ""
    start_line: int = 0  # 1-indexed line number of the opening fence
    raw_info: str = ""  # raw info string after the opening backticks, trimmed


def parse(body: str, *, body_start_line: int = 1, source_path: str = "<string>") -> list[Fence]:
    """Extract all fenced code blocks from `body` in source order.

    `body_start_line` is the 1-indexed line number of the first line of `body`
    in the original source — used to make error messages line up with the
    author's editor.

    Raises `_FenceError` on malformed attribute objects; the compiler
    re-raises these as `MarkdownCompileError`.
    """
    normalized = body.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")

    fences: list[Fence] = []
    i = 0
    while i < len(lines):
        match = _FENCE_OPEN_RE.match(lines[i])
        if match is None:
            i += 1
            continue
        indent = match.group("indent")
        info = match.group("info").strip()
        open_line_no = body_start_line + i

        # Find the matching close. A close fence is any line that is exactly
        # zero-or-more whitespace followed by '```' and no further content.
        close_idx: int | None = None
        for j in range(i + 1, len(lines)):
            stripped = lines[j].rstrip()
            if stripped.lstrip(" \t") == "```":
                close_idx = j
                break
        if close_idx is None:
            raise _FenceError(
                f"{source_path}:{open_line_no}: code fence opened with '```' was never closed."
            )

        raw_body_lines = lines[i + 1 : close_idx]
        stripped_body = _strip_fence_indent(raw_body_lines, indent)
        content = "\n".join(stripped_body)
        if raw_body_lines:
            # Preserve trailing newline so subprocess execution sees the same
            # text the author wrote (CommonMark fences end at the closing
            # line; the convention is to terminate the block body with a
            # newline).
            content += "\n"

        language_token, attributes = _parse_info(info, open_line_no, source_path)
        fences.append(
            Fence(
                language=language_token,
                attributes=attributes,
                content=content,
                start_line=open_line_no,
                raw_info=info,
            )
        )
        i = close_idx + 1

    return fences


def _strip_fence_indent(body_lines: list[str], indent: str) -> list[str]:
    """Strip up to `len(indent)` leading whitespace chars from each body line.

    Matches the standard CommonMark behavior: a fence opened with N columns
    of leading whitespace allows the body to be indented by the same amount
    without that indent becoming part of the rendered code.
    """
    if not indent:
        return list(body_lines)
    width = len(indent)
    stripped: list[str] = []
    for raw in body_lines:
        # Remove up to `width` leading spaces/tabs, but no more — preserves
        # intentional extra indentation in the body.
        cut = 0
        for ch in raw[:width]:
            if ch in (" ", "\t"):
                cut += 1
            else:
                break
        stripped.append(raw[cut:])
    return stripped


def _parse_info(info: str, line_no: int, source_path: str) -> tuple[str, dict[str, Any]]:
    """Split a fence info string into `(language, attributes_dict)`."""
    if not info:
        return "", {}

    # Attribute block is delimited by braces. The language token is whatever
    # precedes the first '{', stripped.
    brace_open = info.find("{")
    if brace_open == -1:
        return info.strip().lower(), {}
    if not info.rstrip().endswith("}"):
        raise _FenceError(
            f"{source_path}:{line_no}: fence attribute block must end with '}}'; got: {info!r}"
        )
    language = info[:brace_open].strip().lower()
    attr_text = info[brace_open:].rstrip()
    try:
        parsed = yaml.safe_load(attr_text)
    except yaml.YAMLError as exc:
        raise _FenceError(
            f"{source_path}:{line_no}: malformed fence attributes {attr_text!r}: {exc}"
        ) from exc
    if not isinstance(parsed, dict):
        raise _FenceError(
            f"{source_path}:{line_no}: fence attributes must be a mapping, got "
            f"{type(parsed).__name__}: {attr_text!r}"
        )
    return language, parsed


class _FenceError(ValueError):
    """Internal exception type. The compiler re-raises as MarkdownCompileError."""
