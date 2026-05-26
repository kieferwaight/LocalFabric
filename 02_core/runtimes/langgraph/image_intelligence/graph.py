"""LangGraph image intelligence workflow with parallel signal extraction."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from core.environment import data
from drivers.sql.schema import assets
from drivers.sql.session import get_connection
from langgraph.graph import END, START, StateGraph
from sqlalchemy import select

_DB_PATH = data("workspace.db")
_DEFAULT_CONCURRENCY = 4
from core.runtimes.langgraph.image_intelligence.nodes import (
    load_asset,
    node_classify,
    node_color,
    node_meta,
    node_quality,
    node_regions,
    node_text,
    node_vision,
    save_report,
)
from core.runtimes.langgraph.types import ImageIntelligenceState

# ── Fan-out / fan-in aggregator ───────────────────────────────────────────────


def run_signals_parallel(state: ImageIntelligenceState) -> ImageIntelligenceState:
    """
    Run the 6 signal tasks concurrently using threads, then merge results back
    into state. LangGraph's Send API works best for subgraphs; for simple
    function-level parallelism, ThreadPoolExecutor is cleaner and sufficient.
    """
    signal_nodes = [
        node_classify,
        node_color,
        node_meta,
        node_quality,
        node_regions,
        node_text,
    ]

    merged = dict(state)
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(fn, state): fn.__name__ for fn in signal_nodes}
        for future in as_completed(futures):
            result = future.result()
            # Merge only the new keys each node produced
            for key in ("classification", "color", "meta", "quality", "regions", "text"):
                if key in result and result[key] is not None:
                    merged[key] = result[key]

    return merged


# ── Build graph ───────────────────────────────────────────────────────────────


def build_image_intelligence_graph() -> Any:
    """Build and compile the image intelligence StateGraph."""
    g = StateGraph(ImageIntelligenceState)

    g.add_node("load_asset", load_asset)
    g.add_node("run_signals", run_signals_parallel)
    g.add_node("vision", node_vision)
    g.add_node("save_report", save_report)

    g.add_edge(START, "load_asset")
    g.add_edge("load_asset", "run_signals")
    g.add_edge("run_signals", "vision")
    g.add_edge("vision", "save_report")
    g.add_edge("save_report", END)

    return g.compile()


# ── Single-image runner ───────────────────────────────────────────────────────


def run_image_intelligence(
    image_path: str,
    asset_id: str | None = None,
    collection: str = "default",
) -> ImageIntelligenceState:
    """Process a single image through the full intelligence pipeline."""
    graph = build_image_intelligence_graph()
    initial: ImageIntelligenceState = {
        "image_path": image_path,
        "asset_id": asset_id,
        "collection": collection,
        "classification": None,
        "color": None,
        "meta": None,
        "quality": None,
        "regions": None,
        "text": None,
        "vision_overview": "",
        "vision_layout": "",
        "vision_style": "",
        "output_path": None,
        "error": None,
    }
    return graph.invoke(initial)


# ── Batch runner ──────────────────────────────────────────────────────────────


def run_batch(
    collection: str,
    concurrency: int | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """
    Load all image assets for *collection* from the registry and process them.

    Parameters
    ----------
    collection:   Collection name to filter assets.
    concurrency:  Number of images to process in parallel (default from settings).
    limit:        Process only the first N images (useful for smoke tests).
    """
    workers = concurrency or _DEFAULT_CONCURRENCY

    # Load image assets from SQLite
    with get_connection(_DB_PATH) as conn:
        rows = conn.execute(
            select(assets).where(
                (assets.c.collection == collection)
                & (assets.c.media_class == "image")
                & (assets.c.is_duplicate == False)  # noqa: E712
            )
        ).fetchall()

    records = [dict(row._mapping) for row in rows]
    if limit:
        records = records[:limit]

    if not records:
        return []

    results: list[dict[str, Any]] = []

    def _process(record: dict) -> dict[str, Any]:
        try:
            result = run_image_intelligence(
                image_path=record["ingested_path"],
                asset_id=record["id"],
                collection=collection,
            )
            return {"asset_id": record["id"], "status": "success", **result}
        except Exception as exc:
            return {"asset_id": record["id"], "status": "failed", "error": str(exc)}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_process, r): r["id"] for r in records}
        for future in as_completed(futures):
            results.append(future.result())

    return results
