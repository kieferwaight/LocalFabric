"""Smoke tests for the markdown runtime CLI adapter."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from core.interfaces.cli.markdown_runtime import main

EXAMPLES = Path(__file__).resolve().parents[1] / "15_examples"


def test_cli_runs_hello_shell_example() -> None:
    rc = main([str(EXAMPLES / "shell.hello.example.md")])
    assert rc == 0


def test_cli_runs_polyglot_example_with_debug(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(
        [
            str(EXAMPLES / "polyglot.hello.example.md"),
            "--name=World",
            "--debug",
        ]
    )
    assert rc == 0
    captured = capsys.readouterr()
    # The debug flag prints the final scope as JSON; the JSON object should be
    # the last thing on stdout and must include the resolved input.
    last_json = _last_json_object(captured.out)
    assert last_json["entity_id"] == "polyglot.hello.example"
    assert last_json["name"] == "World"


def test_cli_returns_nonzero_on_compile_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bad = tmp_path / "bad.md"
    bad.write_text("no frontmatter at all\n")
    rc = main([str(bad)])
    assert rc == 2
    captured = capsys.readouterr()
    assert "error:" in captured.err


def test_cli_no_args_prints_usage(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main([])
    assert rc == 0
    captured = capsys.readouterr()
    assert "Usage:" in captured.out


def test_cli_dash_h_prints_usage(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["-h"])
    assert rc == 0
    captured = capsys.readouterr()
    assert "Usage:" in captured.out


def _last_json_object(text: str) -> dict:
    # The debug dump uses indent=2, so the closing brace lands at column 0 on
    # the last line. Walk backward from that line to find the matching `{` at
    # column 0 — anything else is inside a string value (e.g. the markdown
    # `body` variable).
    lines = text.splitlines()
    end = max(i for i, line in enumerate(lines) if line == "}")
    start = max(i for i in range(end + 1) if lines[i] == "{")
    return json.loads("\n".join(lines[start : end + 1]))
