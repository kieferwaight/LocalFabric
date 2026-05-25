"""
lancedb_driver.py — Tier 2: Persistent file-based vector store backed by LanceDB.

Writes to ~/.local_router_vectors/ by default. No server required — LanceDB
is an embedded library that manages its own files.

Usage:
    from drivers.vector.lancedb_driver import LanceStore

    store = LanceStore()               # connects to default path
    store.add(chunks)                  # list of dicts with "vector" key
    results = store.query(vec, k=5)
    store.delete_source("path/to/file.py")   # remove all chunks from a file
"""

import os
from typing import Optional

from drivers.vector.base import VectorStore

_DEFAULT_DB_PATH = os.path.expanduser("~/.local_router_vectors")
_TABLE_NAME = "chunks"


class LanceStore(VectorStore):
    """
    Persistent vector store using LanceDB.

    Each record stores:
        vector      : list[float]   (embedding)
        text        : str
        source      : str           (file path)
        chunk_index : int
        line_start  : int
        line_end    : int
        strategy    : str           (ast | sliding_window)

    Args:
        db_path:    Directory where LanceDB writes its files.
        table_name: LanceDB table name. Defaults to "chunks".
    """

    def __init__(
        self,
        db_path: str = _DEFAULT_DB_PATH,
        table_name: str = _TABLE_NAME,
    ) -> None:
        try:
            import lancedb
            self._lancedb = lancedb
        except ImportError:
            raise ImportError("LanceDB is required: pip install lancedb")

        self._db_path = db_path
        self._table_name = table_name
        self._db = lancedb.connect(db_path)
        self._table = self._open_or_create_table()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _open_or_create_table(self):
        existing = self._db.table_names()
        if self._table_name in existing:
            return self._db.open_table(self._table_name)
        return None  # created on first add()

    def _ensure_table(self, sample_vector: list[float]):
        """Create the table if it doesn't exist yet (schema is inferred from first row)."""
        if self._table is not None:
            return
        seed_row = {
            "vector": sample_vector,
            "text": "",
            "source": "",
            "chunk_index": 0,
            "line_start": 0,
            "line_end": 0,
            "strategy": "",
        }
        self._table = self._db.create_table(
            self._table_name,
            data=[seed_row],
            mode="create",
        )
        # Remove the seed row so the table starts empty
        self._table.delete("source = ''")

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def add(self, chunks: list[dict]) -> int:
        """
        Persist a list of embedded chunk dicts.
        Each dict must have a "vector" key.
        Skips chunks without a vector.
        Returns the count of records added.
        """
        rows = []
        for chunk in chunks:
            vec = chunk.get("vector")
            if vec is None:
                continue
            rows.append({
                "vector": list(vec),
                "text": chunk.get("text", ""),
                "source": chunk.get("source", ""),
                "chunk_index": int(chunk.get("chunk_index", 0)),
                "line_start": int(chunk.get("line_start", 0)),
                "line_end": int(chunk.get("line_end", 0)),
                "strategy": chunk.get("strategy", ""),
            })

        if not rows:
            return 0

        self._ensure_table(rows[0]["vector"])
        self._table.add(rows)
        return len(rows)

    def delete_source(self, source_path: str) -> None:
        """Remove all chunks that came from a given source file."""
        if self._table is None:
            return
        safe = source_path.replace("'", "''")
        self._table.delete(f"source = '{safe}'")

    def clear(self) -> None:
        """Drop and recreate the table (destructive)."""
        if self._table_name in self._db.table_names():
            self._db.drop_table(self._table_name)
        self._table = None

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
        Return the top-k most similar chunks (cosine / L2 via LanceDB ANN search).

        Args:
            query_vector:   The embedded query (list[float]).
            k:              Number of results to return.
            source_filter:  If set, restrict results to chunks from this source path.

        Returns:
            List of dicts with all chunk fields plus a "score" float (distance).
        """
        if self._table is None:
            return []

        search = self._table.search(query_vector).limit(k)
        if source_filter:
            safe = source_filter.replace("'", "''")
            search = search.where(f"source = '{safe}'")

        try:
            results = search.to_list()
        except Exception as exc:
            print(f"[LanceStore] Query failed: {exc}")
            return []

        output = []
        for row in results:
            record = {k: v for k, v in row.items() if k != "vector"}
            # LanceDB returns _distance; normalize to "score" (lower = better)
            record["score"] = float(row.get("_distance", 0.0))
            output.append(record)
        return output

    # ------------------------------------------------------------------
    # Info
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        if self._table is None:
            return 0
        try:
            return self._table.count_rows()
        except Exception:
            return 0

    def stats(self) -> dict:
        return {
            "db_path": self._db_path,
            "table": self._table_name,
            "entries": len(self),
        }

    def list_sources(self) -> list[str]:
        """Return distinct source file paths indexed in this store."""
        if self._table is None:
            return []
        try:
            rows = self._table.to_pandas()["source"].unique().tolist()
            return rows
        except Exception:
            return []


if __name__ == "__main__":
    store = LanceStore()
    print("LanceStore stats:", store.stats())
