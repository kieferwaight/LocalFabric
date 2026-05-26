"""
drivers.vector — storage-layer drivers for embedded chunks.

Each driver implements the ``VectorStore`` ABC defined in ``base``.
Drivers contain only storage logic; chunking, embedding, and query
orchestration live in ``tasks.embeddings``.

Available drivers:
    lancedb_driver.LanceStore  — Tier 2, persistent (LanceDB embedded files)
    numpy_driver.NumpyStore    — Tier 1, in-memory cosine store
"""

from drivers.vector.base import VectorStore
from drivers.vector.lancedb_driver import LanceStore
from drivers.vector.numpy_driver import NumpyStore

__all__ = ["LanceStore", "NumpyStore", "VectorStore"]
