"""``localfabric`` Typer entry point — composes per-domain sub-apps.

The actual command behaviour lives in the single-domain modules in this
package (``db.py``, ``ingest.py``, ``image_intelligence.py``,
``markdown.py``). This module only wires their Typer sub-apps onto one
root :class:`typer.Typer`.

In Phase C1 this hand-wired composition is replaced by a dynamic walk of
``command.*`` YAML definitions in the runtime catalog. Until then,
adding a domain is still two steps: write ``<domain>.py`` and append it
to :data:`SUB_APPS` below.
"""

from __future__ import annotations

import typer

from core.interfaces.cli.db import db_app
from core.interfaces.cli.image_intelligence import image_intelligence_app
from core.interfaces.cli.ingest import ingest_app
from core.interfaces.cli.markdown import markdown_app

#: Ordered list of (sub-app, mount-name) pairs to mount under the root.
SUB_APPS: list[tuple[typer.Typer, str]] = [
    (db_app, "db"),
    (ingest_app, "ingest"),
    (image_intelligence_app, "image-intelligence"),
    (markdown_app, "markdown"),
]


def build_app() -> typer.Typer:
    """Build the ``localfabric`` Typer app by mounting every sub-app."""
    root = typer.Typer(
        name="localfabric",
        help="Local-first AI workflow platform.",
        no_args_is_help=True,
    )
    for sub_app, name in SUB_APPS:
        root.add_typer(sub_app, name=name)
    return root


app = build_app()


if __name__ == "__main__":
    app()
