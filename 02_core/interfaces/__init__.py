"""User-facing surfaces: CLI, API, MCP.

Each subpackage exposes one interface; the underlying behaviour is shared
via the YAML runtime catalog (see ``core.runtimes.yaml``). Phase C1 of
the restructure replaces hand-wired Typer/FastAPI/FastMCP registrations
with a single ``commands`` module that builds all three from
``command.*`` YAML definitions.
"""
