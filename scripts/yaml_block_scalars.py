#!/usr/bin/env python3
"""Rewrite multi-line YAML string scalars into block-scalar form.

yamlfix canonicalizes most of the catalog but emits multi-line strings as
double-quoted scalars with `\n` escapes; we prefer the literal block
scalar `|` (or folded `>` when the source already chose to fold).

This walks every loaded value, and for any string that contains a newline
substitutes a `LiteralScalarString` so ruamel emits `|`.

Usage:
    python scripts/yaml_block_scalars.py [--check] [path ...]

If no paths are given, walks the repo (excluding .venv, 14_data, 18_docs,
node_modules).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import FoldedScalarString, LiteralScalarString

EXCLUDED_PARTS = {".venv", "14_data", "18_docs", "node_modules", ".git"}


def _promote(node):
    """Recursively rewrite multi-line plain/quoted strings as block scalars."""
    if isinstance(node, dict):
        for k, v in list(node.items()):
            node[k] = _promote(v)
        return node
    if isinstance(node, list):
        for i, v in enumerate(node):
            node[i] = _promote(v)
        return node
    if isinstance(node, (LiteralScalarString, FoldedScalarString)):
        return node
    if isinstance(node, str) and "\n" in node:
        return LiteralScalarString(node)
    return node


def _process(path: Path, *, check: bool) -> bool:
    """Return True if the file is already canonical (no changes needed)."""
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.width = 10_000
    yaml.indent(mapping=2, sequence=2, offset=0)

    original = path.read_text(encoding="utf-8")
    data = yaml.load(original)
    if data is None:
        return True
    _promote(data)

    import io

    buf = io.StringIO()
    yaml.dump(data, buf)
    new = buf.getvalue()

    if new == original:
        return True
    if check:
        print(f"would rewrite: {path}", file=sys.stderr)
        return False
    path.write_text(new, encoding="utf-8")
    print(f"rewrote: {path}")
    return False


def _iter_paths(roots: list[Path]) -> list[Path]:
    out: list[Path] = []
    for root in roots:
        if root.is_file():
            out.append(root)
            continue
        for p in root.rglob("*"):
            if p.suffix not in {".yaml", ".yml"}:
                continue
            if set(p.parts) & EXCLUDED_PARTS:
                continue
            out.append(p)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*", type=Path)
    ap.add_argument("--check", action="store_true", help="exit non-zero if changes would be made")
    args = ap.parse_args(argv)

    roots = args.paths or [Path(".")]
    files = _iter_paths(roots)

    needs_change = 0
    for f in files:
        if not _process(f, check=args.check):
            needs_change += 1

    if args.check and needs_change:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
