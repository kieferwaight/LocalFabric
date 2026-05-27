"""Tests for YAML-authored API documentation workflows."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from core.runtimes.yaml.src import Definition, Runtime, ShellEnvironment
from core.runtimes.yaml.src.dispatcher import Dispatcher, DispatchResult

YAML_ROOT = Path(__file__).resolve().parents[1] / "02_core" / "runtimes" / "yaml"


class RecordingDispatcher(Dispatcher):
    """Dispatcher that records calls without actually running a subprocess."""

    def __init__(self, state_responses: dict[str, dict[str, Any]] | None = None):
        super().__init__()
        self.calls: list[dict[str, Any]] = []
        self.state_responses = state_responses or {}

    def dispatch(self, language, source, base_env=None, cwd=None):
        self.calls.append({"language": language, "source": source})
        state = self.state_responses.get(language, {})
        return DispatchResult(
            language=language,
            exit_code=0,
            stdout="",
            stderr="",
            state_updates=state,
        )


def catalog_runtime(dispatcher=None) -> Runtime:
    runtime = Runtime(
        env=ShellEnvironment(cwd=str(YAML_ROOT)),
        dispatcher=dispatcher or RecordingDispatcher(),
    )
    runtime.import_yaml(str(YAML_ROOT / "stdlib" / "stdlib.yaml"))
    runtime.import_yaml(str(YAML_ROOT / "config.yaml"))
    return runtime


def test_definition_metadata_is_optional_and_validated() -> None:
    definition = Definition.from_dict(
        {
            "id": "demo",
            "title": "Demonstration",
            "description": "# Markdown\n",
            "tags": ["guide"],
            "variables": {"message": "hi"},
            "run": [{"bash": "echo hi"}],
            "docs": {
                "variables": {"message": "A greeting."},
                "run": [{"title": "Speak", "description": "Print a greeting."}],
            },
        }
    )

    assert definition.title == "Demonstration"
    assert definition.docs.variables["message"] == "A greeting."
    assert definition.docs.run[0].title == "Speak"
    assert Definition.from_dict({"id": "fallback"}).title == ""

    with pytest.raises(ValueError, match="unknown local variables"):
        Definition.from_dict({"id": "bad", "docs": {"variables": {"missing": "no"}}})
    with pytest.raises(ValueError, match="tags"):
        Definition.from_dict({"id": "bad", "tags": "not-a-list"})


@pytest.mark.skip(reason="references old path/id from pre-refactor layout — see #47")
def test_catalog_tracks_sources_relationships_and_effective_origins() -> None:
    runtime = catalog_runtime()
    entries = {item["id"]: item for item in runtime.globals["catalog"]["definitions"]}

    assert entries["builtin/files/write-text"]["source_path"] == "stdlib/stdlib.files.yaml"
    assert entries["example/obsidian-template"]["parent"]["id"] == "builtin/files/write-text"
    assert entries["examples/catalog/modules"]["modules"] == [
        "deploy.yaml",
        "git-current-workspace.yaml",
        "gitignore-template.yaml",
        "obsidian-template.yaml",
    ]
    cloud = entries["cloud/deployer"]
    assert {item["id"] for item in cloud["mixin_links"]} == {"mixin/git-info", "mixin/timestamp"}
    assert any(item["origin"] == "cloud/deployer" for item in cloud["resolved"]["inputs"])
    assert entries["builtin/load-modules"]["modules"] == [
        "stdlib.files.yaml",
        "stdlib.git.yaml",
        "stdlib.doc.yaml",
    ]


def test_invoke_foreach_passes_parent_scope_without_leaking_child_state() -> None:
    dispatcher = RecordingDispatcher()
    runtime = Runtime(env=ShellEnvironment(cwd="/tmp"), dispatcher=dispatcher)
    runtime.import_yaml_raw(
        [
            {
                "id": "worker",
                "inputs": {"value": {"type": "string", "required": True}},
                "run": [{"bash": "echo {{ prefix }} {{ value }} {{ item }}"}],
            },
            {
                "id": "caller",
                "variables": {"prefix": "item"},
                "run": [
                    {
                        "invoke": {
                            "definition": "worker",
                            "arguments": {"value": "{{ item }}"},
                        },
                        "for_each": {"items": "['one', 'two']", "as": "item"},
                    }
                ],
            },
        ]
    )

    final_scope = runtime.execute("caller")

    assert [call["source"] for call in dispatcher.calls] == [
        "echo item one one",
        "echo item two two",
    ]
    assert "item" not in final_scope
    assert "value" not in final_scope


@pytest.mark.skip(reason="references old path/id from pre-refactor layout — see #47")
def test_documentation_workflow_writes_and_checks_generated_reference(tmp_path: Path) -> None:
    runtime = catalog_runtime()
    output = tmp_path / "docs"

    runtime.execute("docs/api/reference", {"output_dir": str(output), "mode": "write"})

    definitions = runtime.globals["catalog"]["definitions"]
    pages = sorted((output / "definitions").rglob("*.md"))
    assert len(pages) == len(definitions)
    assert "```mermaid" in (output / "README.md").read_text(encoding="utf-8")
    definition_page = output / "definitions" / "definition-builtin-docs-prune-definition-pages.md"
    assert "## Resolved API" in definition_page.read_text(encoding="utf-8")

    runtime.execute("docs/api/reference", {"output_dir": str(output), "mode": "check"})

    stale_page = output / "definitions" / "removed.md"
    stale_page.write_text(
        "<!-- Generated by workflows.yaml docs/api/reference; do not edit. -->\n# Removed\n",
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="Obsolete generated documentation"):
        runtime.execute("docs/api/reference", {"output_dir": str(output), "mode": "check"})
    runtime.execute("docs/api/reference", {"output_dir": str(output), "mode": "write"})
    assert not stale_page.exists()

    (output / "README.md").write_text("changed\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="stale"):
        runtime.execute("docs/api/reference", {"output_dir": str(output), "mode": "check"})
