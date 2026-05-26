"""
server.py — FastMCP server that registers tools dynamically from the runtime catalog.

Tools are discovered by scanning the YAML command catalog for definitions
whose ``mcp_spec.expose`` is ``true``. Each such command is registered as a
FastMCP tool via ``binder.bind_fastmcp``.

Run via the console script:
    localfabric-mcp

Or directly (stdio transport for Claude Desktop):
    python -m core.interfaces.mcp.server
"""

from __future__ import annotations

import sys
from pathlib import Path


def _ensure_paths() -> None:
    """Prepend the two source roots to sys.path when running without an install."""
    repo_root = Path(__file__).resolve().parents[4]
    for p in (str(repo_root / "02_core"), str(repo_root / "02_core/runtimes/yaml")):
        if p not in sys.path:
            sys.path.insert(0, p)


_ensure_paths()


def main() -> None:
    """Build and run the catalog-driven MCP server over stdio."""
    from mcp.server.fastmcp import FastMCP

    try:
        from core.interfaces.mcp.config import SERVER_NAME
    except ModuleNotFoundError:
        from interfaces.mcp.config import SERVER_NAME  # type: ignore[no-redef]

    try:
        from core.runtimes.yaml.src import Runtime
    except ModuleNotFoundError:
        from src import Runtime  # type: ignore[no-redef]

    try:
        from core.interfaces.commands.registry import CommandRegistry
    except ModuleNotFoundError:
        from interfaces.commands.registry import CommandRegistry  # type: ignore[no-redef]

    try:
        from core.interfaces.commands.binder import bind_fastmcp
    except ModuleNotFoundError:
        from interfaces.commands.binder import bind_fastmcp  # type: ignore[no-redef]

    # ------------------------------------------------------------------
    # (a) Construct the runtime
    # ------------------------------------------------------------------
    _repo_root = Path(__file__).resolve().parents[4]
    _yaml_root = _repo_root / "02_core" / "runtimes" / "yaml"

    runtime = Runtime(workflow_dir=str(_yaml_root))
    runtime.import_yaml(str(_yaml_root / "definitions" / "stdlib.yaml"))
    runtime.execute("stdlib.load-modules.workflow", {})

    # ------------------------------------------------------------------
    # (b) Build the command registry
    # ------------------------------------------------------------------
    registry = CommandRegistry(runtime)

    # ------------------------------------------------------------------
    # (c) Create the FastMCP server
    # ------------------------------------------------------------------
    mcp = FastMCP(SERVER_NAME)

    # ------------------------------------------------------------------
    # (d) Register each MCP-exposed command as a tool
    # ------------------------------------------------------------------
    for cmd in registry.iter_commands():
        if cmd.mcp_spec.get("expose") is True:
            bind_fastmcp(mcp, cmd, runtime)

    # ------------------------------------------------------------------
    # (e) Run over stdio (Claude Desktop transport)
    # ------------------------------------------------------------------
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
