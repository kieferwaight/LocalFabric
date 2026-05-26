"""BDD acceptance criteria from the spec."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from core.runtimes.yaml.src import (
    Runtime,
    ScopeFrame,
    ShellEnvironment,
)
from core.runtimes.yaml.src.dispatcher import Dispatcher, DispatchResult
from core.runtimes.yaml.src.runtime import coerce_type

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


def make_runtime(dispatcher: Dispatcher | None = None) -> Runtime:
    env = ShellEnvironment(cwd="/tmp/test-cwd")
    return Runtime(env=env, dispatcher=dispatcher or RecordingDispatcher())


# ---------- Module library import and runnable examples ----------


def test_stdlib_manifest_loads_namespaced_modules():
    runtime = make_runtime()
    runtime.import_yaml(str(YAML_ROOT / "stdlib" / "stdlib.yaml"))

    assert "builtin/load-modules" in runtime.registry
    assert "builtin/files/write-text" in runtime.registry
    assert "builtin/git/init-current-workspace" in runtime.registry


def test_module_paths_are_relative_to_the_declaring_yaml(tmp_path):
    child = tmp_path / "child.yaml"
    child.write_text("- id: child\n", encoding="utf-8")
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text("- id: loader\n  modules:\n    - child.yaml\n", encoding="utf-8")

    runtime = make_runtime()
    runtime.import_yaml(str(manifest))

    assert list(runtime.registry) == ["loader", "child"]


def test_obsidian_example_writes_core_template_markers(tmp_path):
    runtime = Runtime(env=ShellEnvironment(cwd=str(tmp_path)), dispatcher=Dispatcher())
    runtime.import_yaml(str(YAML_ROOT / "stdlib" / "stdlib.yaml"))
    runtime.import_yaml(str(YAML_ROOT / "examples" / "obsidian-template.yaml"))

    runtime.execute("example/obsidian-template", {"obsidian_folder": str(tmp_path)})

    template = (tmp_path / "Templates" / "daily-note.md").read_text(encoding="utf-8")
    assert "{{date:YYYY-MM-DD}}" in template
    assert "{{date:dddd, MMMM D, YYYY}}" in template


def test_github_example_composes_gitignore_init_and_gh_steps():
    runtime = make_runtime()
    runtime.import_yaml(str(YAML_ROOT / "stdlib" / "stdlib.yaml"))
    runtime.import_yaml(str(YAML_ROOT / "examples" / "git-current-workspace.yaml"))

    assembled = runtime.assemble_definition_frame("example/git/github")

    assert [next(iter(block)) for block in assembled.run] == ["bash", "artifact", "bash"]
    assert "repository_name" in assembled.inputs


# ---------- AC-101.1: Child overrides parent variable, inherits the rest ----------


def test_ac_101_1_child_overrides_parent_variable_and_inherits_rest():
    runtime = make_runtime()
    runtime.import_yaml_raw(
        [
            {
                "id": "parent",
                "variables": {"region": "us-east-1", "replicas": 3},
            },
            {
                "id": "child",
                "extends": "parent",
                "variables": {"region": "eu-west-1"},
            },
        ]
    )
    assembled = runtime.assemble_definition_frame("child")
    assert assembled.variables["region"] == "eu-west-1"
    assert assembled.variables["replicas"] == 3


# ---------- AC-101.2: Deep 3-level inheritance chain ----------


def test_ac_101_2_deep_inheritance_chain():
    runtime = make_runtime()
    runtime.import_yaml_raw(
        [
            {"id": "g", "variables": {"a": "gA", "b": "gB", "c": "gC"}},
            {"id": "p", "extends": "g", "variables": {"b": "pB"}},
            {"id": "c", "extends": "p", "variables": {"c": "cC"}},
        ]
    )
    assembled = runtime.assemble_definition_frame("c")
    assert assembled.variables == {"a": "gA", "b": "pB", "c": "cC"}


# ---------- AC-102.1: Mixin precedence — last mixin wins ----------


def test_ac_102_1_mixin_last_wins():
    runtime = make_runtime()
    runtime.import_yaml_raw(
        [
            {"id": "base", "variables": {"x": "base"}},
            {"id": "m1", "variables": {"x": "m1", "shared": "from-m1"}},
            {"id": "m2", "variables": {"x": "m2"}},
            {
                "id": "leaf",
                "extends": "base",
                "mixins": ["m1", "m2"],
            },
        ]
    )
    assembled = runtime.assemble_definition_frame("leaf")
    assert assembled.variables["x"] == "m2"
    assert assembled.variables["shared"] == "from-m1"


# ---------- AC-201.1: CLI string "5" coerced to int 5 for type=number ----------


def test_ac_201_1_cli_string_coerced_to_number():
    runtime = make_runtime()
    runtime.import_yaml_raw(
        [
            {
                "id": "demo",
                "inputs": {"count": {"type": "number", "required": True}},
                "run": [{"bash": "echo {{ count }}"}],
            }
        ]
    )
    final_scope = runtime.execute("demo", {"count": "5"})
    assert final_scope["count"] == 5
    assert isinstance(final_scope["count"], int)


# ---------- AC-201.2: Missing required input raises clearly before execution ----------


def test_ac_201_2_missing_required_input_raises():
    dispatcher = RecordingDispatcher()
    runtime = make_runtime(dispatcher=dispatcher)
    runtime.import_yaml_raw(
        [
            {
                "id": "demo",
                "inputs": {"service": {"type": "string", "required": True}},
                "run": [{"bash": "echo deploying {{ service }}"}],
            }
        ]
    )
    with pytest.raises(ValueError, match="service"):
        runtime.execute("demo", {})
    # Subprocess should not have been invoked.
    assert dispatcher.calls == []


# ---------- AC-301.1: bash block dispatched to bash binary ----------


def test_ac_301_1_bash_dispatched_to_bash_binary():
    # Use the REAL dispatcher (not RecordingDispatcher) so subprocess.Popen is invoked.
    env = ShellEnvironment(cwd="/tmp/test-cwd")
    runtime = Runtime(env=env, dispatcher=Dispatcher())
    runtime.import_yaml_raw(
        [
            {
                "id": "demo",
                "run": [{"bash": "echo hello"}],
            }
        ]
    )

    captured: dict[str, Any] = {}

    def fake_popen(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["env"] = kwargs.get("env")

        class _Proc:
            returncode = 0
            stdout = type("S", (), {"readline": lambda self: ""})()
            stderr = type("S", (), {"readline": lambda self: ""})()

            def poll(self_inner):
                return 0

            def communicate(self_inner):
                return ("", "")

            def kill(self_inner):  # pragma: no cover
                pass

        return _Proc()

    with patch("core.runtimes.yaml.src.dispatcher.subprocess.Popen", side_effect=fake_popen):
        runtime.execute("demo", {})

    assert captured["cmd"][0:2] == ["/usr/bin/env", "bash"]
    assert "STATE_FILE" in captured["env"]


# ---------- Gap 2.1: Cyclic inheritance raises ValueError ----------


def test_gap_2_1_cyclic_inheritance_detected():
    runtime = make_runtime()
    with pytest.raises(ValueError, match="Cyclic inheritance"):
        runtime.import_yaml_raw(
            [
                {"id": "a", "extends": "b"},
                {"id": "b", "extends": "a"},
            ]
        )


def test_gap_2_1_self_cycle_detected():
    runtime = make_runtime()
    with pytest.raises(ValueError, match="Cyclic inheritance"):
        runtime.import_yaml_raw(
            [
                {"id": "self", "extends": "self"},
            ]
        )


# ---------- Gap 2.3: Type coercion — "false" → False (not truthy string) ----------


def test_gap_2_3_boolean_false_coerces_to_false():
    assert coerce_type("false", "boolean") is False
    assert coerce_type("False", "boolean") is False
    assert coerce_type("FALSE", "boolean") is False
    assert coerce_type("no", "boolean") is False
    assert coerce_type("0", "boolean") is False
    assert coerce_type("", "boolean") is False
    assert coerce_type("true", "boolean") is True
    assert coerce_type("YES", "boolean") is True
    assert coerce_type("1", "boolean") is True
    with pytest.raises(ValueError):
        coerce_type("maybe", "boolean")


# ---------- Bonus: ScopeFrame parent-pointer lookup ----------


def test_scope_frame_walks_parent_chain():
    grandparent = ScopeFrame()
    grandparent.set("planet", "earth")
    parent = ScopeFrame(parent=grandparent)
    parent.set("country", "japan")
    child = ScopeFrame(parent=parent)
    child.set("city", "tokyo")
    assert child.resolve("city") == "tokyo"
    assert child.resolve("country") == "japan"
    assert child.resolve("planet") == "earth"
    with pytest.raises(KeyError):
        child.resolve("missing")


# ---------- Bonus: Multi-pass Jinja rendering ----------


def test_multipass_jinja_renders_referenced_variables():
    runtime = make_runtime()
    runtime.import_yaml_raw(
        [
            {
                "id": "demo",
                "variables": {
                    "a": "hello",
                    "b": "{{ a }} world",
                    "c": "{{ b }}!",
                },
            }
        ]
    )
    scope = runtime.execute("demo", {})
    assert scope["c"] == "hello world!"


# ---------- Bonus: env / runtime namespaces in Jinja context ----------


def test_jinja_exposes_env_and_runtime_namespaces():
    env = ShellEnvironment(cwd="/var/work", args=[], options={}, flags={})
    runtime = Runtime(env=env, dispatcher=RecordingDispatcher())
    runtime.import_yaml_raw(
        [
            {
                "id": "demo",
                "variables": {
                    "where": "{{ env.cwd }}",
                    "ver": "{{ runtime.version }}",
                },
            }
        ]
    )
    scope = runtime.execute("demo", {})
    assert scope["where"] == "/var/work"
    assert scope["ver"] == "1.0.0"


# ---------- Bonus: CLI option parsing ----------


def test_shell_environment_parses_argv():
    env = ShellEnvironment.from_argv(["alpha", "beta", "--region=us-east-1", "--debug", "-v"])
    assert env.args == ["alpha", "beta"]
    assert env.options == {"region": "us-east-1"}
    assert env.flags == {"debug": True, "v": True}


# ---------- Bonus: state bridge merges subprocess output ----------


def test_state_bridge_merges_subprocess_state_into_scope():
    dispatcher = RecordingDispatcher(state_responses={"bash": {"injected": "yes"}})
    runtime = make_runtime(dispatcher=dispatcher)
    runtime.import_yaml_raw(
        [
            {
                "id": "demo",
                "run": [{"bash": "echo hi"}],
            }
        ]
    )
    scope = runtime.execute("demo", {})
    assert scope["injected"] == "yes"
