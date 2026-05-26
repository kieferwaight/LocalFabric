"""CLI adapter — translates argv into a MarkdownHarness invocation.

The adapter is intentionally thin: it parses argv with the YAML runtime's
`ShellEnvironment.from_argv`, instantiates a `Runtime`, auto-imports the
YAML stdlib so authors can `extends: stdlib.*`, and hands off to
`MarkdownHarness.execute`. Lifecycle, retries, and subprocess concerns
belong to the harness, not here.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

from harnesses.markdown import (
    MarkdownCompileError,
    MarkdownHarness,
    ProviderError,
    ProviderResult,
)
from workflows.yaml.src import Runtime, ShellEnvironment

USAGE = (
    "Usage: python -m adapters.cli.markdown <markdown_file> "
    "[positional args] [--key=value] [--flag]"
)

# Default YAML stdlib so that frontmatter `extends: stdlib.*` works without
# the author needing to import anything explicitly. The interpreter for raw
# YAML files uses the same convention.
_YAML_STDLIB = (
    Path(__file__).resolve().parents[2]
    / "06_workflows"
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


def main(argv: list[str] | None = None) -> int:
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
        # Provider-style: write the assistant text to stdout. Tail with a
        # newline if the response doesn't already end in one so the user's
        # shell prompt doesn't run into the response.
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
        # Streaming provider: the harness already echoes each chunk to
        # stdout. Drain the iterator so the API call actually completes.
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


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


if __name__ == "__main__":
    sys.exit(main())
