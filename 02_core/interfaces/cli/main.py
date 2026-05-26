"""``localfabric`` Typer entry point — composes per-domain sub-apps.

Hand-wired sub-apps (``db.py``, ``ingest.py``, ``image_intelligence.py``,
``markdown.py``) are mounted first to preserve backward compatibility with
existing CLI users. Phase C1 adds a second layer that walks the
``command.*`` YAML definitions in the runtime catalog and dynamically
registers additional Typer groups alongside them.

Adding a new YAML-driven verb no longer requires editing this file — only
a ``command.*`` YAML definition with a valid ``argv_spec`` is needed.
"""

from __future__ import annotations

from pathlib import Path

import typer

from core.interfaces.cli.db import db_app
from core.interfaces.cli.image_intelligence import image_intelligence_app
from core.interfaces.cli.ingest import ingest_app
from core.interfaces.cli.markdown import markdown_app

#: Ordered list of (sub-app, mount-name) pairs for hand-wired sub-apps.
SUB_APPS: list[tuple[typer.Typer, str]] = [
    (db_app, "db"),
    (ingest_app, "ingest"),
    (image_intelligence_app, "image-intelligence"),
    (markdown_app, "markdown"),
]

# Path helpers — resolved relative to this file so they work regardless of cwd.
_CLI_DIR = Path(__file__).resolve().parent          # 02_core/interfaces/cli/
_REPO_ROOT = _CLI_DIR.parents[2]                    # ~/src/LocalFabric/
_YAML_RUNTIME_DIR = _REPO_ROOT / "02_core" / "runtimes" / "yaml"
_STDLIB_YAML = _YAML_RUNTIME_DIR / "definitions" / "stdlib.yaml"


def _load_runtime():
    """Construct and boot a YAML Runtime with all standard-library modules loaded."""
    from core.runtimes.yaml.src import Runtime

    r = Runtime(workflow_dir=str(_YAML_RUNTIME_DIR))
    r.import_yaml(str(_STDLIB_YAML))
    r.execute("stdlib.load-modules", {})
    return r


def build_app() -> typer.Typer:
    """Build the ``localfabric`` Typer app.

    Mounts the hand-wired sub-apps first, then iterates the
    :class:`~core.interfaces.commands.registry.CommandRegistry` to register
    any ``command.*`` YAML definitions alongside them.
    """
    from core.interfaces.commands.binder import bind_typer
    from core.interfaces.commands.registry import CommandRegistry

    root = typer.Typer(
        name="localfabric",
        help="Local-first AI workflow platform.",
        no_args_is_help=True,
    )

    for sub_app, name in SUB_APPS:
        root.add_typer(sub_app, name=name)

    # Catalog-driven commands.
    runtime = _load_runtime()
    registry = CommandRegistry(runtime)
    bound_groups: dict[str, typer.Typer] = {}
    for cmd in registry.iter_commands():
        bind_typer(root, cmd, runtime, group_cache=bound_groups)

    return root


app = build_app()


if __name__ == "__main__":
    app()
