"""Tests for the task-attached examples runtime — see
00_specs/03_requirements/add-example-runtime-to-tasks.md."""

from __future__ import annotations

from typing import Any

import pytest
from core.runtimes.yaml.src import Runtime, ShellEnvironment
from core.runtimes.yaml.src.definition import Example
from core.runtimes.yaml.src.dispatcher import Dispatcher, DispatchResult


class RecordingDispatcher(Dispatcher):
    """Dispatcher that records calls without launching a subprocess."""

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


def _make_runtime(dispatcher: Dispatcher | None = None) -> Runtime:
    return Runtime(
        env=ShellEnvironment(cwd="/tmp/test-cwd"),
        dispatcher=dispatcher or RecordingDispatcher(),
    )


# ---------- F1/F2: examples are parsed onto Definition ----------


def test_examples_parsed_from_yaml():
    runtime = _make_runtime()
    runtime.import_yaml_raw(
        [
            {
                "id": "demo.task",
                "inputs": {"path": {"type": "string", "required": True}},
                "examples": [
                    {
                        "id": "example.one",
                        "description": "First case.",
                        "inputs": {"path": "/tmp/a.png"},
                    }
                ],
            }
        ]
    )
    assembled = runtime.assemble_definition_frame("demo.task")
    assert len(assembled.examples) == 1
    assert assembled.examples[0] == Example(
        id="example.one",
        description="First case.",
        inputs={"path": "/tmp/a.png"},
    )


# ---------- F4: example inputs are baseline; explicit args override ----------


def test_example_inputs_used_when_selected():
    dispatcher = RecordingDispatcher()
    runtime = _make_runtime(dispatcher)
    runtime.import_yaml_raw(
        [
            {
                "id": "demo.task",
                "inputs": {"path": {"type": "string", "required": True}},
                "run": [{"python": 'print("{{ path }}")'}],
                "examples": [
                    {"id": "example.one", "inputs": {"path": "/from/example.png"}}
                ],
            }
        ]
    )
    scope = runtime.execute("demo.task", example="example.one")
    assert scope["path"] == "/from/example.png"


def test_explicit_argument_overrides_example_value():
    runtime = _make_runtime()
    runtime.import_yaml_raw(
        [
            {
                "id": "demo.task",
                "inputs": {"path": {"type": "string", "required": True}},
                "run": [{"python": 'print("{{ path }}")'}],
                "examples": [
                    {"id": "example.one", "inputs": {"path": "/from/example.png"}}
                ],
            }
        ]
    )
    scope = runtime.execute(
        "demo.task", arguments={"path": "/explicit.png"}, example="example.one"
    )
    assert scope["path"] == "/explicit.png"


# ---------- F5: unknown example id raises with available IDs ----------


def test_unknown_example_id_raises_with_listing():
    runtime = _make_runtime()
    runtime.import_yaml_raw(
        [
            {
                "id": "demo.task",
                "inputs": {"path": {"type": "string", "required": True}},
                "run": [{"python": 'print("{{ path }}")'}],
                "examples": [
                    {"id": "example.one", "inputs": {"path": "/p.png"}},
                    {"id": "example.two", "inputs": {"path": "/q.png"}},
                ],
            }
        ]
    )
    with pytest.raises(ValueError) as excinfo:
        runtime.execute("demo.task", example="missing")
    msg = str(excinfo.value)
    assert "missing" in msg
    assert "example.one" in msg
    assert "example.two" in msg


def test_unknown_example_id_lists_none_when_no_examples_declared():
    runtime = _make_runtime()
    runtime.import_yaml_raw(
        [
            {
                "id": "demo.task",
                "inputs": {"path": {"type": "string", "required": True}},
                "run": [{"python": 'print("{{ path }}")'}],
            }
        ]
    )
    with pytest.raises(ValueError) as excinfo:
        runtime.execute(
            "demo.task", arguments={"path": "/p.png"}, example="example.one"
        )
    assert "none declared" in str(excinfo.value)


# ---------- F6: examples inherit through `extends:` ----------


def test_examples_inherit_through_extends():
    runtime = _make_runtime()
    runtime.import_yaml_raw(
        [
            {
                "id": "parent",
                "inputs": {"path": {"type": "string", "required": True}},
                "examples": [{"id": "parent.one", "inputs": {"path": "/parent.png"}}],
            },
            {"id": "child", "extends": "parent"},
        ]
    )
    assembled = runtime.assemble_definition_frame("child")
    assert [ex.id for ex in assembled.examples] == ["parent.one"]


def test_child_overrides_parent_example_by_id():
    runtime = _make_runtime()
    runtime.import_yaml_raw(
        [
            {
                "id": "parent",
                "inputs": {"path": {"type": "string", "required": True}},
                "examples": [{"id": "shared", "inputs": {"path": "/parent.png"}}],
            },
            {
                "id": "child",
                "extends": "parent",
                "examples": [{"id": "shared", "inputs": {"path": "/child.png"}}],
            },
        ]
    )
    assembled = runtime.assemble_definition_frame("child")
    shared = next(ex for ex in assembled.examples if ex.id == "shared")
    assert shared.inputs == {"path": "/child.png"}


# ---------- F6: mixins merge examples in order ----------


def test_mixin_examples_merge_in_assembly_order():
    runtime = _make_runtime()
    runtime.import_yaml_raw(
        [
            {
                "id": "base",
                "inputs": {"path": {"type": "string", "required": True}},
            },
            {
                "id": "mix.one",
                "extends": "base",
                "examples": [{"id": "m1", "inputs": {"path": "/m1.png"}}],
            },
            {
                "id": "mix.two",
                "extends": "base",
                "examples": [{"id": "m2", "inputs": {"path": "/m2.png"}}],
            },
            {
                "id": "task",
                "extends": "base",
                "mixins": ["mix.one", "mix.two"],
                "examples": [{"id": "local", "inputs": {"path": "/local.png"}}],
            },
        ]
    )
    assembled = runtime.assemble_definition_frame("task")
    assert [ex.id for ex in assembled.examples] == ["m1", "m2", "local"]


# ---------- N3: compile-time rejection of bad example shape ----------


def test_unknown_input_key_in_example_rejected_at_assembly():
    runtime = _make_runtime()
    runtime.import_yaml_raw(
        [
            {
                "id": "demo.task",
                "inputs": {"path": {"type": "string", "required": True}},
                "examples": [
                    {"id": "bad", "inputs": {"path": "/p.png", "not_declared": 1}}
                ],
            }
        ]
    )
    with pytest.raises(ValueError) as excinfo:
        runtime.assemble_definition_frame("demo.task")
    msg = str(excinfo.value)
    assert "not_declared" in msg
    assert "bad" in msg


def test_duplicate_example_id_rejected_at_parse():
    runtime = _make_runtime()
    with pytest.raises(ValueError) as excinfo:
        runtime.import_yaml_raw(
            [
                {
                    "id": "demo.task",
                    "inputs": {"path": {"type": "string", "required": True}},
                    "examples": [
                        {"id": "same", "inputs": {"path": "/a.png"}},
                        {"id": "same", "inputs": {"path": "/b.png"}},
                    ],
                }
            ]
        )
    assert "duplicate example id" in str(excinfo.value)


def test_example_missing_id_rejected_at_parse():
    runtime = _make_runtime()
    with pytest.raises(ValueError):
        runtime.import_yaml_raw(
            [
                {
                    "id": "demo.task",
                    "inputs": {"path": {"type": "string"}},
                    "examples": [{"description": "no id here"}],
                }
            ]
        )


# ---------- Regression: tasks without examples still work ----------


def test_definition_without_examples_assembles_and_executes():
    runtime = _make_runtime()
    runtime.import_yaml_raw(
        [
            {
                "id": "demo.task",
                "inputs": {"path": {"type": "string", "required": True}},
                "run": [{"python": 'print("{{ path }}")'}],
            }
        ]
    )
    assembled = runtime.assemble_definition_frame("demo.task")
    assert assembled.examples == []
    scope = runtime.execute("demo.task", arguments={"path": "/p.png"})
    assert scope["path"] == "/p.png"


# ---------- The worked example ships and parses ----------


def test_worked_example_on_image_classify_task_loads():
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[1]
    task_path = repo_root / "05_tasks" / "image.classify.task.yaml"
    stdlib_path = (
        repo_root / "02_core" / "runtimes" / "yaml" / "definitions" / "stdlib.yaml"
    )
    runtime = _make_runtime()
    runtime.import_yaml(str(stdlib_path))
    runtime.import_yaml(str(task_path))
    assembled = runtime.assemble_definition_frame("image.classify.task")
    assert any(ex.id == "example.lm-studio-screenshot" for ex in assembled.examples)
