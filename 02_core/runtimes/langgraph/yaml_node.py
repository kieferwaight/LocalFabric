"""Factory that wraps a YAML definition as a LangGraph node function."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from core.runtimes.yaml.src import Runtime


def yaml_node(
    definition_id: str,
    *,
    input_keys: list[str],
    output_key: str,
    runtime: Runtime,
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Return a LangGraph node that runs a YAML definition.

    The returned callable reads ``input_keys`` from the state dict, passes
    them as ``arguments`` to ``runtime.execute(definition_id, ...)``, and
    writes the resulting scope mapping back to ``state[output_key]``.

    The factory validates that ``definition_id`` is present in
    ``runtime.registry`` at call time — fail-fast so misconfiguration is
    caught before the graph is wired up.

    Example:
        runtime = Runtime(workflow_dir="02_core/runtimes/yaml")
        runtime.import_yaml("02_core/runtimes/yaml/definitions/stdlib.yaml")
        runtime.execute("stdlib.load-modules.workflow", {})
        node_fn = yaml_node(
            "stdlib.logger.task",
            input_keys=["message", "level"],
            output_key="logger_result",
            runtime=runtime,
        )
        new_state = node_fn({"message": "hi", "level": "INFO"})
        # new_state["logger_result"] holds the scope returned by execute.
    """
    if definition_id not in runtime.registry:
        raise KeyError(f"yaml_node: unknown definition id {definition_id!r}")

    def _node(state: dict[str, Any]) -> dict[str, Any]:
        for key in input_keys:
            if key not in state:
                raise KeyError(f"yaml_node[{definition_id}]: missing input key {key!r} in state")
        arguments = {key: state[key] for key in input_keys}
        try:
            result = runtime.execute(definition_id, arguments)
        except Exception as exc:
            raise RuntimeError(f"yaml_node[{definition_id}] failed: {exc}") from exc
        return {**state, output_key: result}

    return _node
