"""
tools/embeddings — local embedding pipeline

Modules:
    chunker   — split files into embeddable chunks (AST for .py, sliding window for text/md)
    embedder  — generate vectors via Ollama nomic-embed-text with MD5 dirty-checking
    query     — embed a query and retrieve top-k chunks as a markdown context block
    sweep     — walk a directory tree, chunk + embed all files, persist to store

Storage backends live in ``drivers.vector`` (numpy_driver, lancedb_driver, …);
they implement the ``VectorStore`` ABC and are called by this package.
"""

from .chunker import chunk_file
from .embedder import Embedder, EmbedderUnavailable, EmbeddingExecutor
from .query import LocalKnowledgeQuery

__all__ = [
    "chunk_file",
    "Embedder",
    "EmbedderUnavailable",
    "EmbeddingExecutor",
    "LocalKnowledgeQuery",
]
