"""Node functions for the image intelligence LangGraph workflow."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import insert, update

from core.config import get_settings
from drivers.sql.schema import workflow_runs
from drivers.sql.session import get_connection
from drivers.file import write_json_artifact
from tools.image import classify, color, meta, quality, regions, text_ocr
from workflows.langgraph.types import ImageIntelligenceState
from workflows.langgraph.image_intelligence.vision import describe_image

# ── Node: load_asset ──────────────────────────────────────────────────────────

def load_asset(state: ImageIntelligenceState) -> ImageIntelligenceState:
    """Validate the image path and log the workflow run as 'running'."""
    settings = get_settings()
    path = Path(state["image_path"])

    if not path.exists():
        return {**state, "error": f"Image not found: {path}"}

    run_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    with get_connection(settings.db_path) as conn:
        conn.execute(
            insert(workflow_runs).values(
                id=run_id,
                workflow_name="image_intelligence",
                asset_id=state.get("asset_id"),
                collection=state.get("collection"),
                started_at=now,
                status="running",
            )
        )

    return {**state, "run_id": run_id, "error": None}


# ── Signal nodes (called in parallel via Send) ────────────────────────────────

def node_classify(state: ImageIntelligenceState) -> ImageIntelligenceState:
    path = Path(state["image_path"])
    try:
        return {**state, "classification": classify.classify_image(path)}
    except Exception as exc:
        return {**state, "classification": None, "error": str(exc)}


def node_color(state: ImageIntelligenceState) -> ImageIntelligenceState:
    path = Path(state["image_path"])
    try:
        return {**state, "color": color.extract_color(path)}
    except Exception:
        return {**state, "color": None}


def node_meta(state: ImageIntelligenceState) -> ImageIntelligenceState:
    path = Path(state["image_path"])
    try:
        return {**state, "meta": meta.extract_meta(path)}
    except Exception:
        return {**state, "meta": None}


def node_quality(state: ImageIntelligenceState) -> ImageIntelligenceState:
    path = Path(state["image_path"])
    try:
        return {**state, "quality": quality.extract_quality(path)}
    except Exception:
        return {**state, "quality": None}


def node_regions(state: ImageIntelligenceState) -> ImageIntelligenceState:
    path = Path(state["image_path"])
    try:
        return {**state, "regions": regions.extract_regions(path)}
    except Exception:
        return {**state, "regions": None}


def node_text(state: ImageIntelligenceState) -> ImageIntelligenceState:
    path = Path(state["image_path"])
    try:
        return {**state, "text": text_ocr.extract_text(path)}
    except Exception:
        return {**state, "text": None}


# ── Node: vision ──────────────────────────────────────────────────────────────

def node_vision(state: ImageIntelligenceState) -> ImageIntelligenceState:
    """Run all three vision tasks sequentially through the Ollama harness."""
    path = Path(state["image_path"])
    try:
        descriptions = describe_image(path)
        return {
            **state,
            "vision_overview": descriptions["overview"],
            "vision_layout": descriptions["layout"],
            "vision_style": descriptions["style"],
        }
    except Exception as exc:
        return {
            **state,
            "vision_overview": "",
            "vision_layout": "",
            "vision_style": "",
            "vision_error": str(exc),
        }


# ── Node: save_report ─────────────────────────────────────────────────────────

def save_report(state: ImageIntelligenceState) -> ImageIntelligenceState:
    """Merge all signals into a JSON report and update the workflow run record."""
    settings = get_settings()
    path = Path(state["image_path"])
    collection = state.get("collection", "default")

    report = {
        "asset_id": state.get("asset_id"),
        "file": path.name,
        "path": str(path),
        "collection": collection,
        "generated_at": datetime.now(UTC).isoformat(),
        "classification": state.get("classification"),
        "meta": state.get("meta"),
        "quality": state.get("quality"),
        "color": state.get("color"),
        "text": state.get("text"),
        "regions": state.get("regions"),
        "vision": {
            "overview": state.get("vision_overview", ""),
            "layout": state.get("vision_layout", ""),
            "style": state.get("vision_style", ""),
        },
    }

    # Write to data/outputs/images/<collection>/<stem>__<asset_id>.json
    # so files with identical stems do not overwrite each other.
    out_dir = settings.outputs_root / "images" / collection
    asset_id = state.get("asset_id") or "unknown"
    out_path = out_dir / (f"{path.stem}__{asset_id}.json")
    write_json_artifact(out_path, report)

    # Update the workflow_runs record
    now = datetime.now(UTC)
    run_id = state.get("run_id")
    if run_id:
        with get_connection(settings.db_path) as conn:
            conn.execute(
                update(workflow_runs)
                .where(workflow_runs.c.id == run_id)
                .values(
                    completed_at=now,
                    status="success",
                    output_path=str(out_path),
                )
            )

    return {**state, "output_path": str(out_path)}
