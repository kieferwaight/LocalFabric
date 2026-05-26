#!/usr/bin/env python3
"""CLI entry point for the YAML-driven polyglot runtime interpreter."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src import Runtime, ShellEnvironment  # noqa: E402


USAGE = (
    "Usage: python interpreter.py <yaml_file> <definition_id> "
    "[positional args] [--key=value] [--flag]"
)

WORKFLOW_DIR = Path(__file__).resolve().parent
STDLIB_PATH = WORKFLOW_DIR / "definitions" / "stdlib.yaml"


def parse_cli(argv: list[str]) -> tuple[str, str, list[str]]:
    positional: list[str] = []
    rest: list[str] = []
    for tok in argv:
        if tok.startswith("-"):
            rest.append(tok)
        elif len(positional) < 2:
            positional.append(tok)
        else:
            rest.append(tok)
    if len(positional) < 2:
        raise SystemExit(USAGE)
    return positional[0], positional[1], rest


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        print(USAGE)
        return 0

    yaml_file, definition_id, remainder = parse_cli(argv)
    env = ShellEnvironment.from_argv(remainder)
    debug = bool(env.flags.get("debug"))

    runtime = Runtime(
        env=env,
        system_debug=debug,
        workflow_dir=WORKFLOW_DIR,
        definition_page_format="core.runtimes.yaml.definition.{flat_id}.md",
        index_page="core.runtimes.yaml.api.md",
        schema_page="core.runtimes.yaml.schema.md",
    )
    if STDLIB_PATH.exists():
        runtime.import_yaml(str(STDLIB_PATH))
    runtime.import_yaml(yaml_file)

    arguments: dict[str, object] = dict(env.options)
    final_scope = runtime.execute(definition_id, arguments)

    if debug:
        print(json.dumps(_jsonable(final_scope), indent=2, default=str))
    return 0


def _jsonable(value):
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


if __name__ == "__main__":
    sys.exit(main())
