"""LangGraph ingestion workflow: scan → classify → hash → dedup → copy → register."""

from __future__ import annotations

from typing import Any

from core.runtimes.langgraph.ingest.nodes import (
    classify,
    copy_assets,
    deduplicate,
    hash_files,
    register,
    scan,
)
from core.runtimes.langgraph.types import IngestState
from langgraph.graph import END, START, StateGraph

# ── Build graph ───────────────────────────────────────────────────────────────


def build_ingest_graph() -> Any:
    """Build and compile the ingestion StateGraph."""
    g = StateGraph(IngestState)

    g.add_node("scan", scan)
    g.add_node("classify", classify)
    g.add_node("hash_files", hash_files)
    g.add_node("deduplicate", deduplicate)
    g.add_node("copy_assets", copy_assets)
    g.add_node("register", register)

    g.add_edge(START, "scan")
    g.add_edge("scan", "classify")
    g.add_edge("classify", "hash_files")
    g.add_edge("hash_files", "deduplicate")
    g.add_edge("deduplicate", "copy_assets")
    g.add_edge("copy_assets", "register")
    g.add_edge("register", END)

    return g.compile()


# ── Public runner ─────────────────────────────────────────────────────────────


def run_ingest(
    source_dir: str,
    collection: str,
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    Run the ingestion workflow and return the final state.

    Parameters
    ----------
    source_dir:  Absolute path to the source folder to scan.
    collection:  Short name for this dataset (e.g. "sequoia-waste").
    dry_run:     If True, skip copying and DB writes; just report what would happen.
    """
    graph = build_ingest_graph()
    initial_state: IngestState = {
        "source_dir": source_dir,
        "collection": collection,
        "dry_run": dry_run,
        "scanned_files": [],
        "classified_files": [],
        "hashed_files": [],
        "deduplicated": [],
        "copied_files": [],
        "registered_count": 0,
        "errors": [],
    }
    return graph.invoke(initial_state)
