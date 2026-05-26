"""End-to-end tests for MarkdownHarness — integration with the YAML runtime."""

from __future__ import annotations

from pathlib import Path

import pytest
from core.runtimes.markdown import MarkdownCompileError, MarkdownHarness
from core.runtimes.yaml.src import Runtime

FIXTURES = Path(__file__).resolve().parent / "fixtures"
STDLIB = (
    Path(__file__).resolve().parents[1]
    / "02_core"
    / "runtimes"
    / "yaml"
    / "definitions"
    / "stdlib.yaml"
)


def _runtime_with_stdlib() -> Runtime:
    runtime = Runtime()
    runtime.import_yaml(str(STDLIB))
    return runtime


def test_compile_file_matches_compile_text() -> None:
    harness = MarkdownHarness()
    path = FIXTURES / "minimal.md"
    via_file = harness.compile_file(path)
    via_text = harness.compile_text(path.read_text(), source_path=str(path))
    assert via_file == via_text


def test_register_inserts_into_runtime_registry() -> None:
    harness = MarkdownHarness()
    def_id = harness.register(FIXTURES / "minimal.md")
    assert def_id == "tests.minimal"
    assert "tests.minimal" in harness.runtime.registry


def test_register_dir_returns_ids_in_stable_order(tmp_path: Path) -> None:
    # Copy two fixtures into a temp dir with deterministic alphabetical names.
    (tmp_path / "a.md").write_text((FIXTURES / "minimal.md").read_text())
    second = (FIXTURES / "with_inputs.md").read_text()
    (tmp_path / "b.md").write_text(second)
    harness = MarkdownHarness()
    ids = harness.register_dir(tmp_path)
    assert ids == ["tests.minimal", "tests.with-inputs"]


def test_register_dir_skips_malformed_files(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    (tmp_path / "good.md").write_text((FIXTURES / "minimal.md").read_text())
    (tmp_path / "bad.md").write_text((FIXTURES / "invalid_missing_id.md").read_text())
    harness = MarkdownHarness()
    import logging

    with caplog.at_level(logging.WARNING, logger="core.runtimes.markdown"):
        ids = harness.register_dir(tmp_path)
    assert ids == ["tests.minimal"]
    assert any("Skipping" in rec.message for rec in caplog.records)


def test_execute_runs_shell_block_end_to_end() -> None:
    harness = MarkdownHarness()
    scope = harness.execute(FIXTURES / "minimal.md")
    # The bash block prints, but state-bridge is empty; verify the scope at
    # least carries the entity_id and body variable.
    assert scope["entity_id"] == "tests.minimal"
    assert "echo minimal" in scope["body"]


def test_execute_propagates_compile_errors() -> None:
    harness = MarkdownHarness()
    with pytest.raises(MarkdownCompileError):
        harness.execute(FIXTURES / "invalid_missing_id.md")


def test_execute_propagates_missing_required_input() -> None:
    harness = MarkdownHarness()
    with pytest.raises(ValueError, match="Missing required input"):
        harness.execute(FIXTURES / "with_inputs.md", arguments={})


def test_execute_passes_arguments_through() -> None:
    harness = MarkdownHarness()
    scope = harness.execute(FIXTURES / "with_inputs.md", arguments={"name": "world"})
    assert scope["name"] == "world"


def test_execute_polyglot_state_bridge_merges() -> None:
    harness = MarkdownHarness()
    scope = harness.execute(FIXTURES / "polyglot.md", arguments={"name": "Alice"})
    assert scope["name"] == "Alice"
    assert scope["py_saw"] == "Alice"


def test_extends_stdlib_runs_inherited_blocks() -> None:
    runtime = _runtime_with_stdlib()
    harness = MarkdownHarness(runtime=runtime)
    scope = harness.execute(FIXTURES / "extends_stdlib.md")
    # The inherited run block executes `command`; scope should reflect the
    # command's working_dir variable being bound (stdlib.run-command.task resolves
    # it from env.cwd by default).
    assert scope["command"] == "echo from-stdlib"


def test_compile_file_missing_frontmatter() -> None:
    harness = MarkdownHarness()
    with pytest.raises(MarkdownCompileError):
        harness.compile_file(FIXTURES / "invalid_no_frontmatter.md")


def test_compile_file_duplicate_ids() -> None:
    harness = MarkdownHarness()
    with pytest.raises(MarkdownCompileError, match="duplicate"):
        harness.compile_file(FIXTURES / "invalid_duplicate_ids.md")


def test_register_dir_non_directory_raises(tmp_path: Path) -> None:
    file = tmp_path / "a.md"
    file.write_text((FIXTURES / "minimal.md").read_text())
    harness = MarkdownHarness()
    with pytest.raises(NotADirectoryError):
        harness.register_dir(file)


def test_runtime_default_is_constructed_when_omitted() -> None:
    harness = MarkdownHarness()
    assert isinstance(harness.runtime, Runtime)
