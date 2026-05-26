"""``localfabric`` Typer entry point — composes per-domain CLI adapters.

The actual command behaviour lives in the single-domain adapter classes
in this bucket (``db_adapter.py``, ``ingest_adapter.py``,
``image_intelligence_adapter.py``, ``markdown_adapter.py``). This module
only wires their Typer sub-apps onto one root :class:`typer.Typer`.

Adding a new domain is two steps:

1. Write a new ``<domain>_adapter.py`` with a :class:`CliAdapter` subclass
   and one :class:`CliCommand` subclass per verb.
2. Append the adapter class to :data:`ADAPTERS` below.
"""

from __future__ import annotations

import typer

from adapters.cli.base import CliAdapter
from adapters.cli.db_adapter import DbCliAdapter
from adapters.cli.image_intelligence_adapter import ImageIntelligenceCliAdapter
from adapters.cli.ingest_adapter import IngestCliAdapter
from adapters.cli.markdown_adapter import MarkdownCliAdapter

#: Ordered list of CLI adapters mounted under the root ``localfabric`` app.
#: Append new single-domain adapters here.
ADAPTERS: list[type[CliAdapter]] = [
    DbCliAdapter,
    IngestCliAdapter,
    ImageIntelligenceCliAdapter,
    MarkdownCliAdapter,
]


def build_app() -> typer.Typer:
    """Build the ``localfabric`` Typer app by mounting every registered adapter."""
    root = typer.Typer(
        name="ai-utils",
        help="Local-first AI workflow platform.",
        no_args_is_help=True,
    )
    for adapter_cls in ADAPTERS:
        root.add_typer(adapter_cls.build_typer(), name=adapter_cls.mount_name())
    return root


app = build_app()


if __name__ == "__main__":
    app()
