"""
tasks/embeddings — local embedding pipeline

Modules:
    chunker   — split files into embeddable chunks (AST for .py, sliding window for text/md)
    embedder  — generate vectors via Ollama nomic-embed-text with MD5 dirty-checking
    query     — embed a query and retrieve top-k chunks as a markdown context block
    sweep     — atomic helpers: collect_files, file_hash, load_manifest, save_manifest

Storage backends live in ``drivers.vector`` (numpy_driver, lancedb_driver, …);
they implement the ``VectorStore`` ABC and are called by this package.

The full sweep orchestration (collect → chunk → embed → upsert → persist manifest)
lives in ``06_workflows/embeddings-sweep.yaml``.
"""

from .chunker import chunk_file
from .embedder import Embedder, EmbedderUnavailable, EmbeddingExecutor
from .query import LocalKnowledgeQuery
from .sweep import collect_files, file_hash, load_manifest, save_manifest

__all__ = [
    "chunk_file",
    "Embedder",
    "EmbedderUnavailable",
    "EmbeddingExecutor",
    "LocalKnowledgeQuery",
    "collect_files",
    "file_hash",
    "load_manifest",
    "save_manifest",
]
