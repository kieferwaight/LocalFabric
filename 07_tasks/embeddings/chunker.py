"""
chunker.py — Split source files into embeddable text chunks.

Strategies:
  - Python (.py)          : AST-based, one chunk per top-level function/class definition.
                            Falls back to sliding window if ast.parse fails.
  - Markdown/text/yaml    : Sliding window of WINDOW_TOKENS tokens with OVERLAP_RATIO overlap.
  - Everything else       : Sliding window on raw lines.

Each chunk is returned as a dict:
    {
        "text":       str,   # the chunk content
        "source":     str,   # absolute file path
        "chunk_index": int,  # 0-based index within this file
        "line_start": int,   # 1-based first line of this chunk
        "line_end":   int,   # 1-based last line of this chunk (inclusive)
        "strategy":   str,   # "ast" | "sliding_window"
    }
"""

import ast
import os
from typing import Generator

WINDOW_TOKENS = 512       # approximate tokens per sliding-window chunk
OVERLAP_RATIO = 0.10      # 10 % overlap between consecutive windows
CHARS_PER_TOKEN = 4       # rough heuristic: 1 token ≈ 4 characters

WINDOW_CHARS = WINDOW_TOKENS * CHARS_PER_TOKEN
STEP_CHARS = int(WINDOW_CHARS * (1 - OVERLAP_RATIO))

# File extensions that use the sliding-window strategy
SLIDING_WINDOW_EXTS = {
    ".md", ".txt", ".rst", ".yaml", ".yml", ".toml", ".json",
    ".sh", ".bash", ".zsh", ".env", ".cfg", ".ini", ".conf",
}


def _sliding_window_chunks(
    text: str, source: str, strategy: str = "sliding_window"
) -> Generator[dict, None, None]:
    """Yield fixed-size overlapping chunks from raw text."""
    lines = text.splitlines(keepends=True)
    # Build a char-offset → line-number lookup for fast slicing
    char_offsets = []
    running = 0
    for line in lines:
        char_offsets.append(running)
        running += len(line)

    def char_to_line(char_pos: int) -> int:
        """Return 1-based line number for a character offset (binary search)."""
        lo, hi = 0, len(char_offsets) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if char_offsets[mid] <= char_pos:
                lo = mid
            else:
                hi = mid - 1
        return lo + 1  # 1-based

    start = 0
    idx = 0
    total = len(text)

    while start < total:
        end = min(start + WINDOW_CHARS, total)
        chunk_text = text[start:end].strip()
        if chunk_text:
            line_start = char_to_line(start)
            line_end = char_to_line(end - 1) if end > start else line_start
            yield {
                "text": chunk_text,
                "source": source,
                "chunk_index": idx,
                "line_start": line_start,
                "line_end": line_end,
                "strategy": strategy,
            }
            idx += 1
        if end >= total:
            break
        start += STEP_CHARS


def _ast_chunks(text: str, source: str) -> Generator[dict, None, None]:
    """
    Yield one chunk per top-level function/class definition using Python's AST.
    Module-level code outside any def/class is emitted as a single leading chunk.
    Falls back to sliding_window if parsing fails.
    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        yield from _sliding_window_chunks(text, source, strategy="sliding_window")
        return

    lines = text.splitlines()
    covered_lines: set[int] = set()
    idx = 0

    top_level_nodes = [
        node for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        and isinstance(getattr(node, "col_offset", None), int)
        and node.col_offset == 0  # truly top-level (not nested)
    ]
    # Sort by source line
    top_level_nodes.sort(key=lambda n: n.lineno)

    for node in top_level_nodes:
        start_line = node.lineno          # 1-based
        end_line = node.end_lineno        # 1-based, inclusive
        chunk_lines = lines[start_line - 1 : end_line]
        chunk_text = "\n".join(chunk_lines).strip()

        if not chunk_text:
            continue

        # If the chunk is very long, sub-chunk with sliding window
        if len(chunk_text) > WINDOW_CHARS * 2:
            for sub in _sliding_window_chunks(chunk_text, source, strategy="ast"):
                sub["chunk_index"] = idx
                # Adjust line numbers to absolute file positions
                sub["line_start"] = start_line + sub["line_start"] - 1
                sub["line_end"] = start_line + sub["line_end"] - 1
                yield sub
                idx += 1
        else:
            yield {
                "text": chunk_text,
                "source": source,
                "chunk_index": idx,
                "line_start": start_line,
                "line_end": end_line,
                "strategy": "ast",
            }
            idx += 1

        covered_lines.update(range(start_line, end_line + 1))

    # Emit module-level code not inside any top-level def/class
    module_lines = [
        (i + 1, line)
        for i, line in enumerate(lines)
        if (i + 1) not in covered_lines
    ]
    if module_lines:
        module_text = "\n".join(line for _, line in module_lines).strip()
        if module_text:
            first_line = module_lines[0][0]
            last_line = module_lines[-1][0]
            if len(module_text) > WINDOW_CHARS * 2:
                for sub in _sliding_window_chunks(module_text, source, strategy="ast"):
                    sub["chunk_index"] = idx
                    sub["line_start"] = first_line + sub["line_start"] - 1
                    sub["line_end"] = first_line + sub["line_end"] - 1
                    yield sub
                    idx += 1
            else:
                yield {
                    "text": module_text,
                    "source": source,
                    "chunk_index": idx,
                    "line_start": first_line,
                    "line_end": last_line,
                    "strategy": "ast",
                }


def chunk_file(path: str) -> list[dict]:
    """
    Read a file and return a list of chunk dicts.
    Returns an empty list if the file cannot be read or yields no content.
    """
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return []

    if not text.strip():
        return []

    source = os.path.abspath(path)
    ext = os.path.splitext(path)[1].lower()

    if ext == ".py":
        chunks = list(_ast_chunks(text, source))
        if not chunks:  # fallback if AST produced nothing
            chunks = list(_sliding_window_chunks(text, source))
    elif ext in SLIDING_WINDOW_EXTS:
        chunks = list(_sliding_window_chunks(text, source))
    else:
        # Binary or unknown — attempt sliding window on raw text
        chunks = list(_sliding_window_chunks(text, source))

    return chunks


if __name__ == "__main__":
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else __file__
    results = chunk_file(target)
    print(f"File: {target}  →  {len(results)} chunks")
    for c in results[:3]:
        preview = c["text"][:80].replace("\n", " ")
        print(f"  [{c['chunk_index']}] L{c['line_start']}-{c['line_end']} ({c['strategy']}): {preview}…")
