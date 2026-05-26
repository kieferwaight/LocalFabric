"""Abstract base class for all adapters.

An adapter translates **one external interface** (CLI, REST, OpenAI API,
MCP, …) into internal capability calls. The shape mirrors the
``Harness`` base in [04_harnesses/base.py](../04_harnesses/base.py):
each adapter is a class, each adapter is single-domain, each adapter
sits in a bucket named after its interface.

Concrete adapters declare two class-level fields:

* ``interface`` — the interface family (``"cli"``, ``"rest"``, ``"mcp"``).
  All adapters in a given bucket share the same value (``cli/*`` adapters
  all have ``interface = "cli"``).
* ``domain`` — the single slice of behaviour the adapter covers
  (``"ingest"``, ``"db"``, ``"image_intelligence"``). One domain per
  adapter, no exceptions; if you reach for a second domain, write a
  second adapter.

The Python ``Protocol`` form of the adapter contract lives in
[01_interfaces/adapter.py](../01_interfaces/adapter.py); concrete
adapters here may or may not implement ``to_request``/``from_response``
depending on whether they sit in front of the dispatch schemas or call
workflows/harnesses directly.
"""

from __future__ import annotations

import abc
import logging
from typing import Any, ClassVar, Mapping


class AdapterError(RuntimeError):
    """Raised for adapter-level failures (parsing, translation, dispatch)."""


class Adapter(abc.ABC):
    """Base class for all adapters.

    Subclasses set the ``interface`` and ``domain`` class variables and
    implement whatever entry shape the interface requires (a Typer
    sub-app for CLI, an HTTP route table for REST, an MCP server for
    MCP, …). Concrete entry methods live on the interface-specific
    subclass — see :class:`adapters.cli.base.CliAdapter`.
    """

    #: Interface family this adapter exposes. Set by the per-interface
    #: subclass (e.g. ``"cli"`` on :class:`CliAdapter`).
    interface: ClassVar[str] = "adapter"

    #: Single domain this adapter covers. Set by the concrete subclass.
    domain: ClassVar[str] = "adapter"

    def __init__(self, config: Mapping[str, Any] | None = None) -> None:
        self.config: dict[str, Any] = dict(config or {})
        self._logger = logging.getLogger(f"adapter.{self.interface}.{self.domain}")

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"<{type(self).__name__} interface={self.interface!r} domain={self.domain!r}>"
