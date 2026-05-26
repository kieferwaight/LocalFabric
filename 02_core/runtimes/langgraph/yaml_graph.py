"""Compiler that turns a YAML workflow definition into a LangGraph StateGraph."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from core.runtimes.langgraph.yaml_node import yaml_node
from core.runtimes.yaml.src import Runtime
from langgraph.graph import END, START, StateGraph


def compile_graph(
    workflow_definition_id: str,
    *,
    runtime: Runtime,
    state_schema: type | None = None,
) -> Any:
    """Compile a YAML workflow def into a runnable LangGraph StateGraph.

    The workflow def must be tagged ``[workflow, langgraph]`` and its
    ``run:`` block must be a list of ``invoke:`` entries (each invoking a
    YAML task definition).  Each invoke becomes one node in the StateGraph,
    wired in declaration order with a single START → … → END edge chain.

    ``state_schema`` is the TypedDict passed to ``StateGraph(schema)``. If
    omitted, defaults to a generic ``dict[str, Any]`` schema (StateGraph
    accepts ``dict`` directly for ad-hoc workflows).

    Each invoke entry's ``arguments`` mapping is treated as ``input_keys``
    for the corresponding node: the keys of ``arguments`` are the state
    keys the task expects to read. The task's output is written back to
    ``state[<node_name>]``, where ``<node_name>`` is the invoke's
    ``definition`` id (sanitized to a valid Python identifier by replacing
    ``.`` with ``_``).

    Constraints
    -----------
    Only ``invoke:`` blocks are supported in the workflow ``run:`` list.
    Raw ``bash:``, ``python:``, ``render:``, or any other block type will
    raise a ``ValueError``.  Author those steps as YAML task definitions
    and invoke them instead.
    """
    assembled = runtime.assemble_definition_frame(workflow_definition_id)

    if "workflow" not in assembled.tags or "langgraph" not in assembled.tags:
        raise ValueError(
            f"compile_graph: definition {workflow_definition_id!r} must be tagged"
            " [workflow, langgraph]; got tags={assembled.tags!r}"
        )

    invokes: list[tuple[str, Callable[[dict[str, Any]], dict[str, Any]]]] = []
    # Track how many times each sanitized base name has been used so that
    # duplicate invocations of the same definition get unique node names
    # (e.g. ``stdlib_logger_0``, ``stdlib_logger_1``).
    name_counts: dict[str, int] = {}

    for block in assembled.run:
        if not isinstance(block, dict) or "invoke" not in block:
            raise ValueError(
                f"compile_graph: only 'invoke:' blocks are supported in a"
                f" [workflow, langgraph] definition; got block keys={list(block)!r}"
                f" in {workflow_definition_id!r}"
            )
        invoke = block["invoke"]
        if not isinstance(invoke, dict) or "definition" not in invoke:
            raise ValueError(
                f"compile_graph: each invoke block must have a 'definition' key"
                f" in {workflow_definition_id!r}"
            )
        definition_id: str = str(invoke["definition"])
        arguments: dict[str, Any] = dict(invoke.get("arguments") or {})
        base_name: str = definition_id.replace(".", "_")
        count = name_counts.get(base_name, 0)
        name_counts[base_name] = count + 1
        node_name: str = f"{base_name}_{count}" if count > 0 else base_name
        fn = yaml_node(
            definition_id,
            input_keys=list(arguments.keys()),
            output_key=node_name,
            runtime=runtime,
        )
        invokes.append((node_name, fn))

    schema = state_schema if state_schema is not None else dict
    g: StateGraph = StateGraph(schema)
    prev: Any = START
    for node_name, fn in invokes:
        g.add_node(node_name, fn)
        g.add_edge(prev, node_name)
        prev = node_name
    g.add_edge(prev, END)
    return g.compile()
