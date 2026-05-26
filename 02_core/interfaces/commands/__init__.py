"""Python glue that turns ``command.*`` YAML definitions into CLI / API / MCP handlers.

``registry.py`` scans the runtime catalog for entries with ``has_command=True``
and exposes them as :class:`~registry.Command` dataclasses.

``binder.py`` consumes those dataclasses and registers handlers on a
:class:`typer.Typer` app (CLI), a FastAPI app (Phase C3), or a FastMCP server
(Phase C4) by reading each command's ``argv_spec``, ``http_spec``, and
``mcp_spec`` variables.
"""
