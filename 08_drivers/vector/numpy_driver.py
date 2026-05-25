"""
numpy_driver.py — Tier 1: In-memory vector store backed by NumPy.

Zero infrastructure. Everything lives in RAM for the lifetime of the process.
Ideal for prototyping or queries over a small corpus (< ~5 000 chunks).

Usage:
    from drivers.vector.numpy_driver import NumpyStore

    store = NumpyStore()
    store.add(chunks)              # list of dicts with "vector" and "text" keys
    results = store.query(vec, k=5)
    store.save("my_store.npz")     # optional: persist to disk
    store.load("my_store.npz")     # reload
"""

from typing import Optional

from drivers.vector.base import VectorStore

try:
    import numpy as np
    _NUMPY_OK = True
except ImportError:
    _NUMPY_OK = False
    np = None  # type: ignore


class NumpyStore(VectorStore):
    """
    In-memory cosine-similarity vector store.

    Each entry stores:
        vector  : np.ndarray  (1-D float32)
        text    : str
        source  : str         (file path)
        metadata: dict        (any extra keys from the chunk dict)
    """

    def __init__(self) -> None:
        if not _NUMPY_OK:
            raise ImportError("NumPy is required: pip install numpy")
        self._vectors: list[np.ndarray] = []
        self._records: list[dict] = []

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def add(self, chunks: list[dict]) -> int:
        """
        Add a list of embedded chunk dicts.
        Each dict must have a "vector" key (list[float] or np.ndarray).
        Returns the number of entries added.
        """
        added = 0
        for chunk in chunks:
            vec = chunk.get("vector")
            if vec is None:
                continue
            arr = np.array(vec, dtype=np.float32)
            self._vectors.append(arr)
            record = {k: v for k, v in chunk.items() if k != "vector"}
            self._records.append(record)
            added += 1
        return added

    def clear(self) -> None:
        self._vectors.clear()
        self._records.clear()

    def delete_source(self, source_path: str) -> None:
        """Remove all records originating from ``source_path``."""
        keep_vectors: list[np.ndarray] = []
        keep_records: list[dict] = []
        for vec, rec in zip(self._vectors, self._records):
            if rec.get("source") != source_path:
                keep_vectors.append(vec)
                keep_records.append(rec)
        self._vectors = keep_vectors
        self._records = keep_records

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def query(
        self,
        query_vector: list[float],
        k: int = 5,
        source_filter: Optional[str] = None,
    ) -> list[dict]:
        """
        Return the top-k most similar records to *query_vector* (cosine similarity).
        Each result dict includes all original metadata plus a "score" float.

        If ``source_filter`` is provided, results are restricted to records
        whose ``source`` field matches (client-side filtering after ranking).
        """
        if not self._vectors:
            return []

        q = np.array(query_vector, dtype=np.float32)
        q_norm = np.linalg.norm(q)
        if q_norm == 0:
            return []

        matrix = np.stack(self._vectors)               # (N, D)
        norms = np.linalg.norm(matrix, axis=1)         # (N,)
        # Avoid division by zero
        safe_norms = np.where(norms == 0, 1e-10, norms)
        scores = (matrix @ q) / (safe_norms * q_norm)  # cosine similarity

        top_indices = np.argsort(scores)[::-1][:k]
        results = []
        for idx in top_indices:
            record = dict(self._records[idx])
            record["score"] = float(scores[idx])
            results.append(record)

        if source_filter:
            results = [r for r in results if r.get("source") == source_filter]
        return results

    # ------------------------------------------------------------------
    # Persistence (optional)
    # ------------------------------------------------------------------

    def save(self, path: str) -> None:
        """Persist store to a .npz file."""
        if not self._vectors:
            print("[NumpyStore] Nothing to save.")
            return
        matrix = np.stack(self._vectors).astype(np.float32)
        import json
        records_json = json.dumps(self._records)
        np.savez_compressed(path, vectors=matrix, records=np.array([records_json]))
        print(f"[NumpyStore] Saved {len(self._vectors)} entries → {path}")

    def load(self, path: str) -> None:
        """Load a previously saved .npz store."""
        import json
        data = np.load(path, allow_pickle=True)
        matrix = data["vectors"]
        records_json = str(data["records"][0])
        self._records = json.loads(records_json)
        self._vectors = [matrix[i] for i in range(matrix.shape[0])]
        print(f"[NumpyStore] Loaded {len(self._vectors)} entries from {path}")

    # ------------------------------------------------------------------
    # Info
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        return len(self._vectors)

    def stats(self) -> dict:
        return {
            "entries": len(self._vectors),
            "dims": self._vectors[0].shape[0] if self._vectors else None,
        }

    def list_sources(self) -> list[str]:
        """Return distinct source paths currently indexed."""
        seen: list[str] = []
        seen_set: set[str] = set()
        for rec in self._records:
            src = rec.get("source")
            if src and src not in seen_set:
                seen_set.add(src)
                seen.append(src)
        return seen


if __name__ == "__main__":
    store = NumpyStore()
    print("NumpyStore ready. Entries:", len(store))
