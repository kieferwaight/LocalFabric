"""
base.py — Minimal protocol/ABC for vector store drivers.

A ``VectorStore`` provides a uniform interface over different storage backends
(in-memory NumPy, embedded LanceDB, remote Qdrant, etc.) so that higher-level
tools (sweep, query) can switch backends transparently.

Concrete drivers in this package implement this ABC:

* ``drivers.vector.numpy_driver.NumpyStore``    — in-memory NumPy backend
* ``drivers.vector.lancedb_driver.LanceStore``  — persistent LanceDB backend
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class VectorStore(ABC):
    """
    Minimal interface every vector store driver must implement.

    Drivers store embedded chunk dicts. Each chunk has at minimum:
        vector       : list[float] | ndarray
        text         : str
        source       : str        (originating file path)
        chunk_index  : int
        line_start   : int
        line_end     : int
        strategy     : str        ("ast" | "sliding_window")

    Optional capabilities (``delete_source``, ``list_sources``) ship as
    no-op defaults so callers like ``tasks.embeddings.sweep`` can call them
    unconditionally; drivers should override when they can do better.
    """

    # ------------------------------------------------------------------
    # Core: mutation
    # ------------------------------------------------------------------

    @abstractmethod
    def add(self, chunks: list[dict]) -> int:
        """
        Persist a list of embedded chunk dicts.
        Each dict must carry a ``"vector"`` key; chunks missing it are skipped.
        Returns the number of records actually added.
        """

    @abstractmethod
    def clear(self) -> None:
        """Remove all entries from the store (destructive)."""

    # ------------------------------------------------------------------
    # Core: retrieval
    # ------------------------------------------------------------------

    @abstractmethod
    def query(
        self,
        query_vector: list[float],
        k: int = 5,
        source_filter: Optional[str] = None,
    ) -> list[dict]:
        """
        Return up to ``k`` chunk dicts most similar to ``query_vector``.

        Each result dict mirrors the original chunk fields (minus ``vector``)
        and adds a ``score`` float. Score semantics are backend-dependent:
        cosine similarity (higher = better) for NumPy, distance
        (lower = better) for LanceDB-style ANN.

        ``source_filter`` optionally restricts results to a single source path.
        Drivers that cannot push this filter down should still honor it
        (filtering client-side is acceptable).
        """

    # ------------------------------------------------------------------
    # Core: introspection
    # ------------------------------------------------------------------

    @abstractmethod
    def __len__(self) -> int:
        """Number of records currently stored."""

    @abstractmethod
    def stats(self) -> dict:
        """Backend-specific summary (entry count, path, dims, etc.)."""

    # ------------------------------------------------------------------
    # Optional capabilities (safe defaults)
    # ------------------------------------------------------------------

    def delete_source(self, source_path: str) -> None:
        """Remove all chunks originating from ``source_path``. Default: no-op."""
        return None

    def list_sources(self) -> list[str]:
        """Return distinct source paths indexed in this store. Default: []."""
        return []
