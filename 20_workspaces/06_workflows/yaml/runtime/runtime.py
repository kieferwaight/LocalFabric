"""Runtime VM that assembles definition frames and executes them."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Set

from .compiler import Compiler
from .definition import Definition, InputConstraint
from .dispatcher import Dispatcher
from .jinja_engine import JinjaEngine
from .scope_frame import ScopeFrame
from .shell_environment import ShellEnvironment


VERSION = "1.0.0"


def coerce_type(val: Any, expected_type: str) -> Any:
    if val is None:
        return None
    if expected_type == "boolean":
        if isinstance(val, bool):
            return val
        s = str(val).strip().lower()
        if s in ("true", "yes", "1"):
            return True
        if s in ("false", "no", "0", ""):
            return False
        raise ValueError(f"Cannot coerce {val!r} to boolean.")
    if expected_type == "number":
        if isinstance(val, bool):
            raise ValueError(f"Cannot coerce {val!r} to number.")
        if isinstance(val, (int, float)):
            return val
        try:
            s = str(val)
            return int(s) if "." not in s else float(s)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Cannot coerce {val!r} to number.") from exc
    if expected_type == "array":
        if isinstance(val, list):
            return list(val)
        return [item.strip() for item in str(val).split(",")]
    return str(val)


class Runtime:
    def __init__(
        self,
        env: Optional[ShellEnvironment] = None,
        dispatcher: Optional[Dispatcher] = None,
        jinja_engine: Optional[JinjaEngine] = None,
        system_debug: bool = False,
    ) -> None:
        self.env: ShellEnvironment = env or ShellEnvironment()
        self.registry: Dict[str, Definition] = {}
        self.imported_yaml_files: Set[str] = set()
        self.compiler = Compiler(self.registry)
        self.dispatcher = dispatcher or Dispatcher()
        self.jinja = jinja_engine or JinjaEngine()
        self.globals: Dict[str, Any] = {
            "version": VERSION,
            "system_debug": system_debug,
            "registry": list(self.registry.keys()),
        }
        # Expose jinja_env attribute for spec compliance.
        self.jinja_env = self.jinja.env

    # --- YAML import ----------------------------------------------------

    def import_yaml(self, file_path: str) -> List[Definition]:
        normalized_path = os.path.realpath(os.path.abspath(file_path))
        if normalized_path in self.imported_yaml_files:
            return []

        self.imported_yaml_files.add(normalized_path)
        try:
            loaded = self.compiler.import_file(normalized_path)
            for definition in list(loaded):
                for module in definition.modules:
                    module_path = os.path.join(os.path.dirname(normalized_path), module)
                    loaded.extend(self.import_yaml(module_path))
        except Exception:
            self.imported_yaml_files.discard(normalized_path)
            raise
        self.globals["registry"] = list(self.registry.keys())
        return loaded

    def import_yaml_raw(self, raw: object) -> List[Definition]:
        loaded = self.compiler.import_raw(raw)
        self.globals["registry"] = list(self.registry.keys())
        return loaded

    # --- Definition assembly --------------------------------------------

    def assemble_definition_frame(self, def_id: str) -> Definition:
        if def_id not in self.registry:
            raise KeyError(f"Unknown definition id: {def_id!r}")
        self.compiler.detect_cycle(def_id, set(), set())
        return self._assemble(def_id, set())

    def _assemble(self, def_id: str, in_progress: Set[str]) -> Definition:
        if def_id in in_progress:
            raise ValueError(f"Cyclic inheritance detected: {def_id} forms a loop.")
        in_progress.add(def_id)

        original = self.registry[def_id]

        # Order: base_parent → mixin1 → mixin2 → ... → local. Child overrides parent.
        variables: Dict[str, Any] = {}
        inputs: Dict[str, InputConstraint] = {}
        run: List[Dict[str, str]] = []
        teardown: List[Dict[str, str]] = []

        if original.extends:
            parent = self._assemble(original.extends, in_progress)
            variables.update(parent.variables)
            inputs.update(parent.inputs)
            run.extend(parent.run)
            teardown.extend(parent.teardown)

        for mixin_id in original.mixins:
            mixin = self._assemble(mixin_id, in_progress)
            variables.update(mixin.variables)
            inputs.update(mixin.inputs)
            run.extend(mixin.run)
            teardown.extend(mixin.teardown)

        # Local overrides everything.
        variables.update(original.variables)
        inputs.update(original.inputs)
        if original.run:
            run = list(original.run)
        if original.teardown:
            teardown = list(original.teardown)

        in_progress.remove(def_id)
        return Definition(
            id=original.id,
            extends=original.extends,
            mixins=list(original.mixins),
            modules=list(original.modules),
            run=run,
            variables=variables,
            inputs=inputs,
            teardown=teardown,
        )

    # --- Execution ------------------------------------------------------

    def execute(
        self,
        def_id: str,
        arguments: Optional[Dict[str, Any]] = None,
        parent_scope: Optional[ScopeFrame] = None,
    ) -> Dict[str, Any]:
        arguments = dict(arguments or {})
        assembled = self.assemble_definition_frame(def_id)

        scope = ScopeFrame(parent=parent_scope)
        scope.set("entity_id", def_id)

        # 1. Apply input constraints — coerce types, fill defaults, enforce required.
        coerced_inputs = self._resolve_inputs(assembled.inputs, arguments, scope)
        for k, v in coerced_inputs.items():
            scope.set(k, v)

        # 2. Render variables via multi-pass Jinja; bind into scope as we go so later
        # variables can reference earlier ones.
        for name, raw_val in assembled.variables.items():
            ctx = scope.build_jinja_context(self.globals, self.env)
            scope.set(name, self.jinja.render_value(raw_val, ctx))

        # 3. Execute run blocks; teardown runs in finally regardless of outcome.
        try:
            self._run_blocks(assembled.run, scope)
        finally:
            if assembled.teardown:
                try:
                    self._run_blocks(assembled.teardown, scope)
                except Exception as teardown_exc:  # pragma: no cover - defensive
                    import sys
                    sys.stderr.write(f"Teardown failed: {teardown_exc}\n")

        return dict(scope.local_store)

    def _resolve_inputs(
        self,
        constraints: Dict[str, InputConstraint],
        arguments: Dict[str, Any],
        scope: ScopeFrame,
    ) -> Dict[str, Any]:
        resolved: Dict[str, Any] = {}
        # First pass: render defaults that might reference env/runtime.
        for name, constraint in constraints.items():
            if name in arguments and arguments[name] is not None:
                resolved[name] = coerce_type(arguments[name], constraint.type)
            elif constraint.default is not None:
                ctx = scope.build_jinja_context(self.globals, self.env)
                rendered = self.jinja.render_value(constraint.default, ctx)
                resolved[name] = coerce_type(rendered, constraint.type)
            elif constraint.required:
                raise ValueError(
                    f"Missing required input {name!r} (type={constraint.type})."
                )
        return resolved

    def _run_blocks(self, blocks: List[Dict[str, str]], scope: ScopeFrame) -> None:
        for block in blocks:
            if not isinstance(block, dict) or len(block) != 1:
                raise ValueError(
                    "Each run block must be a single-key mapping like {bash: '...'}."
                )
            language, source = next(iter(block.items()))
            if not self.dispatcher.supports(language):
                raise ValueError(f"Unsupported language in run block: {language!r}")
            ctx = scope.build_jinja_context(self.globals, self.env)
            rendered_source = self.jinja.render(source, ctx)
            result = self.dispatcher.dispatch(
                language,
                rendered_source,
                base_env=self.env.env,
                cwd=self.env.cwd,
            )
            if result.state_updates:
                scope.update(result.state_updates)
