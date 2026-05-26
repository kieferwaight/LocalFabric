"""FastAPI factory + uvicorn entry for localfabric.

The HTTP surface mirrors the CLI: every command.* YAML definition with
a non-empty http_spec is exposed as a route on this app. Adding a new
HTTP endpoint is one YAML edit — no Python here changes.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI

_CLI_DIR = Path(__file__).resolve().parent          # 02_core/interfaces/api/
_REPO_ROOT = _CLI_DIR.parents[2]                    # ~/src/LocalFabric/
_YAML_RUNTIME_DIR = _REPO_ROOT / "02_core" / "runtimes" / "yaml"
_STDLIB_YAML = _YAML_RUNTIME_DIR / "definitions" / "stdlib.yaml"


def _load_runtime():
    from core.runtimes.yaml.src import Runtime
    r = Runtime(workflow_dir=str(_YAML_RUNTIME_DIR))
    r.import_yaml(str(_STDLIB_YAML))
    r.execute("stdlib.load-modules", {})
    return r


def build_app() -> FastAPI:
    """Build the FastAPI app: scan the runtime catalog, register one
    route per command with a populated http_spec."""
    from core.interfaces.commands.binder import bind_fastapi
    from core.interfaces.commands.registry import CommandRegistry

    runtime = _load_runtime()
    app = FastAPI(
        title="LocalFabric API",
        description="HTTP mirror of the localfabric CLI command surface.",
        version="0.1.0",
    )
    registry = CommandRegistry(runtime)
    for cmd in registry.iter_commands():
        if not cmd.http_spec.get("path"):
            continue
        bind_fastapi(app, cmd, runtime)
    return app


def cli_main() -> None:
    """Uvicorn entry for the localfabric-api console script."""
    import uvicorn
    host = os.environ.get("LOCALFABRIC_API_HOST", "127.0.0.1")
    port = int(os.environ.get("LOCALFABRIC_API_PORT", "8765"))
    uvicorn.run(
        "core.interfaces.api.app:app",
        host=host,
        port=port,
        reload=False,
    )


app = build_app()
