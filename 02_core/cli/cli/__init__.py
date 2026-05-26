"""CLI adapter bucket — one class per domain, one ``CliCommand`` per verb.

See [base.py](base.py) for the :class:`CliAdapter` and :class:`CliCommand`
base classes. See [main.py](main.py) for the ``localfabric`` Typer
composition. The raw markdown-runtime entry (``localfabric-md``) lives
in [markdown_runtime_adapter.py](markdown_runtime_adapter.py).
"""

from adapters.cli.base import CliAdapter, CliCommand
from adapters.cli.db_adapter import DbCliAdapter, DbInitCommand
from adapters.cli.image_intelligence_adapter import (
    ImageIntelligenceCliAdapter,
    ImageIntelligenceRunCommand,
    ImageIntelligenceSingleCommand,
)
from adapters.cli.ingest_adapter import IngestCliAdapter, IngestRunCommand
from adapters.cli.markdown_adapter import MarkdownCliAdapter, MarkdownFormatCommand

# The markdown runtime adapter is intentionally not re-exported here — it is
# its own ``python -m`` entry point (``localfabric-md``), and eagerly
# importing it from this package would emit a runpy double-import warning
# when invoked that way. Import it directly from ``markdown_runtime_adapter``.

__all__ = [
    "CliAdapter",
    "CliCommand",
    "DbCliAdapter",
    "DbInitCommand",
    "ImageIntelligenceCliAdapter",
    "ImageIntelligenceRunCommand",
    "ImageIntelligenceSingleCommand",
    "IngestCliAdapter",
    "IngestRunCommand",
    "MarkdownCliAdapter",
    "MarkdownFormatCommand",
]
