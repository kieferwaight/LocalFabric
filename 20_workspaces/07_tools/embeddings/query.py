"""
query.py — Query the local vector store and return a grounded markdown context block.

Ties together Embedder + a store backend to produce a formatted context snippet
ready to be injected into a frontier model prompt.

Usage:
    from tools.embeddings.query import LocalKnowledgeQuery

    lkq = LocalKnowledgeQuery()          # uses LanceDB by default
    context_md = lkq.query("how do I run tests?", k=4)
    print(context_md)

Or as a standalone CLI:
    python query.py "how do I run tests?"
"""

import os
from typing import Literal, Optional

from tools.embeddings.embedder import Embedder, EmbedderUnavailable

StoreBackend = Literal["lancedb", "numpy"]

_CONTEXT_HEADER = "<!-- [Local Knowledge Base Context] -->"
_CONTEXT_FOOTER = "<!-- [End Local Knowledge Base Context] -->"


class LocalKnowledgeQuery:
    """
    High-level query interface over the local vector store.

    Args:
        backend:    "lancedb" (persistent, default) or "numpy" (in-memory, for testing).
        store_path: Path override for LanceDB db directory (ignored for numpy).
        model:      Ollama embedding model to use.
        k:          Default number of results to return.
    """

    def __init__(
        self,
        backend: StoreBackend = "lancedb",
        store_path: Optional[str] = None,
        model: str = "nomic-embed-text",
        k: int = 5,
    ) -> None:
        self.k = k
        self._embedder = Embedder(model=model)
        self._store = self._init_store(backend, store_path)

    def _init_store(self, backend: StoreBackend, store_path: Optional[str]):
        if backend == "numpy":
            from drivers.vector.numpy_driver import NumpyStore
            return NumpyStore()
        else:
            from drivers.vector.lancedb_driver import LanceStore
            kwargs = {}
            if store_path:
                kwargs["db_path"] = store_path
            return LanceStore(**kwargs)

    # ------------------------------------------------------------------
    # Core query
    # ------------------------------------------------------------------

    def query(
        self,
        query_text: str,
        k: Optional[int] = None,
        source_filter: Optional[str] = None,
        min_score: Optional[float] = None,
        as_markdown: bool = True,
    ) -> str | list[dict]:
        """
        Embed *query_text* and retrieve the top-k most relevant chunks.

        Args:
            query_text:    The natural-language question or task description.
            k:             Override default result count.
            source_filter: Restrict results to a specific source file path.
            min_score:     Filter results below this cosine similarity score
                           (only applies to NumpyStore; LanceDB uses distance).
            as_markdown:   If True (default), return a formatted markdown context block.
                           If False, return the raw list of result dicts.

        Returns:
            str  — formatted markdown context block (as_markdown=True)
            list — raw result dicts             (as_markdown=False)
        """
        k = k or self.k

        try:
            query_vec = self._embedder.embed(query_text)
        except EmbedderUnavailable as exc:
            if as_markdown:
                return f"<!-- [Local Knowledge Base] Embedder unavailable: {exc} -->"
            return []

        # All drivers accept the unified VectorStore.query signature; the
        # base class guarantees ``source_filter`` is honored (even if filtered
        # client-side by simpler backends).
        results = self._store.query(query_vec, k=k, source_filter=source_filter)

        # Optional score threshold — only meaningful for backends where
        # higher score = better match (e.g. NumpyStore cosine similarity).
        # LanceDB returns distances (lower = better) so the threshold is skipped.
        if min_score is not None:
            from drivers.vector.numpy_driver import NumpyStore
            if isinstance(self._store, NumpyStore):
                results = [r for r in results if r.get("score", 0) >= min_score]

        if not as_markdown:
            return results

        return self._format_markdown(query_text, results)

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

    def _format_markdown(self, query: str, results: list[dict]) -> str:
        if not results:
            return (
                f"{_CONTEXT_HEADER}\n"
                f"No relevant context found for: {query!r}\n"
                f"{_CONTEXT_FOOTER}"
            )

        lines = [_CONTEXT_HEADER, f"Query: {query!r}", ""]
        for i, r in enumerate(results, start=1):
            source = r.get("source", "unknown")
            rel_source = _relative_path(source)
            line_start = r.get("line_start", "?")
            line_end = r.get("line_end", "?")
            score = r.get("score")
            score_str = f"  (score: {score:.4f})" if score is not None else ""
            text = r.get("text", "").strip()

            lines.append(f"### Result {i} — `{rel_source}` L{line_start}–{line_end}{score_str}")
            lines.append("")
            lines.append("```")
            lines.append(text)
            lines.append("```")
            lines.append("")

        lines.append(_CONTEXT_FOOTER)
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Store access (for sweep.py and other writers)
    # ------------------------------------------------------------------

    @property
    def store(self):
        return self._store

    @property
    def embedder(self):
        return self._embedder


def _relative_path(path: str) -> str:
    """Try to return a path relative to CWD; fall back to basename."""
    try:
        return os.path.relpath(path)
    except ValueError:
        return os.path.basename(path)


if __name__ == "__main__":
    import sys

    query_text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "how do I run tests?"
    lkq = LocalKnowledgeQuery()
    print(lkq.query(query_text))
