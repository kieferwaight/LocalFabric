#!/usr/bin/env python3
"""CLI entry point for the YAML-driven polyglot runtime interpreter."""

from __future__ import annotations

import json
import os
import sys

try:
    from workflows.yaml.runtime import Runtime, ShellEnvironment
except ModuleNotFoundError:
    import importlib.util
    from pathlib import Path

    workspace_root = Path(__file__).resolve().parents[2]
    drivers_init = workspace_root / "08_drivers" / "__init__.py"
    spec = importlib.util.spec_from_file_location(
        "drivers",
        drivers_init,
        submodule_search_locations=[str(drivers_init.parent)],
    )
    if spec is None or spec.loader is None:
        raise
    drivers = importlib.util.module_from_spec(spec)
    sys.modules["drivers"] = drivers
    spec.loader.exec_module(drivers)
    # Direct invocation from this folder is the documented YAML workflow interface.
    from runtime import Runtime, ShellEnvironment


USAGE = (
    "Usage: python interpreter.py <yaml_file> <definition_id> "
    "[positional args] [--key=value] [--flag]"
)


def parse_cli(argv: list[str]) -> tuple[str, str, list[str]]:
    """Split argv into (yaml_file, definition_id, remainder).

    The first two positional values are mandatory.
    """
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

    runtime = Runtime(env=env, system_debug=debug)

    stdlib_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stdlib", "stdlib.yaml")
    if os.path.exists(stdlib_path):
        runtime.import_yaml(stdlib_path)
    runtime.import_yaml(yaml_file)

    arguments: dict[str, object] = dict(env.options)
    # Positional args are exposed via env.args; we also pass them as 'args'.
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
