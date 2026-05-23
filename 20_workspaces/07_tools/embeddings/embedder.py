"""Generate embeddings through an injected harness and persist cache via a driver."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Protocol

from drivers.cache import JsonCache
from harnesses.base import HarnessError
from harnesses.ollama import OllamaHarness


_DEFAULT_MODEL = "nomic-embed-text"
_DEFAULT_CACHE = (
    Path(__file__).resolve().parents[2] / "14_data" / "cache" / "embeddings" / "embed_cache.json"
)


class EmbeddingExecutor(Protocol):
    def embed(self, text: str, model: str | None = None) -> list[float]: ...


class EmbedderUnavailable(RuntimeError):
    """Raised when embedding execution cannot be completed."""


class Embedder:
    """Generate and cache embeddings while delegating execution and storage."""

    def __init__(
        self,
        model: str = _DEFAULT_MODEL,
        cache_path: str | Path = _DEFAULT_CACHE,
        batch_size: int = 32,
        executor: EmbeddingExecutor | None = None,
    ) -> None:
        self.model = model
        self.cache_path = str(cache_path)
        self.batch_size = batch_size
        self._executor = executor or OllamaHarness({"model": model, "manage_server": False})
        self._cache_driver = JsonCache(cache_path)
        self._cache: dict[str, list[float]] = self._cache_driver.load()
        self._dirty = False

    def _save_cache(self) -> None:
        if not self._dirty:
            return
        try:
            self._cache_driver.write(self._cache)
            self._dirty = False
        except OSError as exc:
            print(f"[Embedder] Warning: could not save cache: {exc}")

    @staticmethod
    def _hash(text: str) -> str:
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def _execute(self, text: str) -> list[float]:
        try:
            return self._executor.embed(text, model=self.model)
        except (HarnessError, OSError) as exc:
            raise EmbedderUnavailable(f"Embedding failed: {exc}") from exc

    def embed(self, text: str, bypass_cache: bool = False) -> list[float]:
        """Return an embedding vector for text, consulting the cache first."""
        key = self._hash(text)
        if not bypass_cache and key in self._cache:
            return self._cache[key]
        vector = self._execute(text)
        self._cache[key] = vector
        self._dirty = True
        return vector

    def embed_chunks(
        self,
        chunks: list[dict],
        bypass_cache: bool = False,
        verbose: bool = False,
    ) -> list[dict]:
        """Attach embedding vectors to chunk dictionaries."""
        total = len(chunks)
        for index, chunk in enumerate(chunks):
            if not bypass_cache and "vector" in chunk:
                continue
            if verbose:
                print(
                    f"[Embedder] {index + 1}/{total} - "
                    f"{chunk.get('source', '?')} chunk {chunk.get('chunk_index', index)}"
                )
            chunk["vector"] = self.embed(chunk["text"], bypass_cache=bypass_cache)
        self._save_cache()
        return chunks

    def cache_stats(self) -> dict:
        return {"entries": len(self._cache), "path": self.cache_path, "model": self.model}

    def flush_cache(self) -> None:
        self._dirty = True
        self._save_cache()

    def clear_cache(self) -> None:
        self._cache = {}
        self._dirty = False
        self._cache_driver.clear()
