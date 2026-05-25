"""
Driver interface — Python Protocol for storage backends in 08_drivers.

Drivers normalize read/write/query access to filesystem-backed targets
(SQLite files, Postgres folders, Qdrant indices, LanceDB stores, etc.).
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class DriverProtocol(Protocol):
    """Minimal driver shape: accept a path target and a few CRUD primitives."""

    def initialize(self, target: str) -> None:
        """Create the backing store if missing. Idempotent."""
        ...

    def read(self, key: str) -> Any: ...
    def write(self, key: str, value: Any) -> None: ...
    def query(self, **kwargs: Any) -> list[Any]: ...
    def stats(self) -> dict[str, Any]: ...
