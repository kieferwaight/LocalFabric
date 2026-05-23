"""
drivers.vector — storage-layer drivers for embedded chunks.

Each driver implements the ``VectorStore`` ABC defined in ``base``.
Drivers contain only storage logic; chunking, embedding, and query
orchestration live in ``tools.embeddings``.

Available drivers:
    lancedb_driver.LanceStore  — Tier 2, persistent (LanceDB embedded files)
    numpy_driver.NumpyStore    — Tier 1, in-memory cosine store
"""

from drivers.vector.base import VectorStore

__all__ = ["VectorStore"]
