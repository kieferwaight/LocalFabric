"""``localfabric-md`` — raw markdown prompt runtime entry.

Translates raw argv into a :class:`core.runtimes.markdown.MarkdownHarness`
invocation. The entry is intentionally thin — argv parsing,
``ShellEnvironment`` construction, and result rendering — while
compilation, retries, and provider/subprocess concerns live in the
harness.

This is a separate entry from ``localfabric markdown format`` (the
Typer formatting workflow in ``markdown.py``): the raw runtime has its
own argv shape ``<file> [args] [--key=value]`` inherited from the YAML
runtime's :class:`ShellEnvironment`, so it lives outside the Typer tree.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

from core.runtimes.markdown import (
    MarkdownCompileError,
    MarkdownHarness,
    ProviderError,
    ProviderResult,
)
from core.runtimes.yaml.src import Runtime, ShellEnvironment

USAGE = (
    "Usage: localfabric-md <markdown_file> "
    "[positional args] [--key=value] [--flag]"
)

# Default YAML stdlib so authors can `extends: stdlib.*` from frontmatter
# without an explicit import. The path resolves the repo root from this
# file's location (02_core/interfaces/cli/markdown_runtime.py → repo root
# is parents[3]).
_YAML_STDLIB = (
    Path(__file__).resolve().parents[3]
    / "02_core"
    / "runtimes"
    / "yaml"
    / "definitions"
    / "stdlib.yaml"
)


def _parse_positional(argv: list[str]) -> tuple[str, list[str]]:
    file_arg: str | None = None
    rest: list[str] = []
    for tok in argv:
        if tok.startswith("-"):
            rest.append(tok)
        elif file_arg is None:
            file_arg = tok
        else:
            rest.append(tok)
    if file_arg is None:
        raise SystemExit(USAGE)
    return file_arg, rest


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def main(argv: list[str] | None = None) -> int:
    """Entry point used by the ``localfabric-md`` script and tests."""
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        print(USAGE)
        return 0

    markdown_file, remainder = _parse_positional(argv)
    env = ShellEnvironment.from_argv(remainder)
    debug = bool(env.flags.get("debug"))
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    runtime = Runtime(env=env, system_debug=debug)
    if _YAML_STDLIB.exists():
        runtime.import_yaml(str(_YAML_STDLIB))

    harness = MarkdownHarness(runtime=runtime)
    try:
        result = harness.execute(markdown_file, dict(env.options))
    except MarkdownCompileError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except ProviderError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3

    if isinstance(result, ProviderResult):
        sys.stdout.write(result.text)
        if result.text and not result.text.endswith("\n"):
            sys.stdout.write("\n")
        sys.stdout.flush()
        if debug:
            print(
                json.dumps(
                    {"model": result.model, "usage": result.usage},
                    indent=2,
                    default=str,
                ),
                file=sys.stderr,
            )
        return 0

    if not isinstance(result, dict):
        # Streaming provider: harness already echoes each chunk to
        # stdout. Drain the iterator so the call actually completes.
        try:
            for _ in result:
                pass
        except ProviderError as exc:
            print(f"\nerror: {exc}", file=sys.stderr)
            return 3
        sys.stdout.write("\n")
        sys.stdout.flush()
        return 0

    if debug:
        print(json.dumps(_jsonable(result), indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
