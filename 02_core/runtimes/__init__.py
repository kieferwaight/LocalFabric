"""Workflow runtimes — YAML, Markdown, LangGraph.

All three normalise to YAML: ``yaml`` is the execution engine, ``markdown``
compiles markdown prompts into YAML definitions, and ``langgraph`` exposes
the stateful-graph runtime plus the bridge that runs YAML tasks as nodes.

The runtime catalog (``core.runtimes.yaml.Runtime.globals['catalog']``) is
the single source of truth every interface (CLI, API, MCP) introspects.
"""
