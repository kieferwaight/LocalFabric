"""core.interfaces.mcp — Catalog-driven FastMCP server.

Registers MCP tools dynamically from the YAML command catalog rather than
hardcoding them.  Any ``command.*`` definition with ``mcp_spec.expose: true``
in the catalog is automatically surfaced as an MCP tool.

Entry point (console script):  ``localfabric-mcp``
Direct invocation:             ``python -m core.interfaces.mcp.server``
Config helper:                 ``python -m core.interfaces.mcp.config``
"""
