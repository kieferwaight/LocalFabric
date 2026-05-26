"""Node functions for the asset ingestion LangGraph workflow."""

from __future__ import annotations

import hashlib
import mimetypes
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func, insert, select

from core.paths import data
from drivers.sql.schema import assets
from drivers.sql.session import get_connection
from drivers.file import copy_asset
from workflows.langgraph.types import IngestState

_DB_PATH = data("workspace.db")
_INPUTS_ROOT = data("inputs")

# ── Media classification ──────────────────────────────────────────────────────

_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".tiff", ".tif", ".bmp"}
_DOCUMENT_EXTS = {".pdf", ".docx", ".doc", ".txt", ".md"}


def _media_class(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in _IMAGE_EXTS:
        return "image"
    if ext in _DOCUMENT_EXTS:
        return "document"
    return "unknown"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ── Node: scan ────────────────────────────────────────────────────────────────

def scan(state: IngestState) -> IngestState:
    """Walk the source directory and collect all file entries."""
    source_dir = Path(state["source_dir"])
    if not source_dir.is_dir():
        return {**state, "errors": state.get("errors", []) + [f"Source not found: {source_dir}"]}

    scanned: list[dict] = []
    for p in sorted(source_dir.rglob("*")):
        if p.is_file() and not p.name.startswith("."):
            scanned.append(
                {
                    "original_path": str(p),
                    "filename": p.name,
                    "size_bytes": p.stat().st_size,
                }
            )

    return {**state, "scanned_files": scanned}


# ── Node: classify ────────────────────────────────────────────────────────────

def classify(state: IngestState) -> IngestState:
    """Assign media_class and mime_type to each scanned file."""
    classified: list[dict] = []
    for item in state.get("scanned_files", []):
        p = Path(item["original_path"])
        mime, _ = mimetypes.guess_type(str(p))
        classified.append(
            {
                **item,
                "extension": p.suffix.lstrip(".").lower(),
                "mime_type": mime,
                "media_class": _media_class(p),
            }
        )
    return {**state, "classified_files": classified}


# ── Node: hash_files ──────────────────────────────────────────────────────────

def hash_files(state: IngestState) -> IngestState:
    """Compute SHA-256 and derive asset_id for each file."""
    hashed: list[dict] = []
    for item in state.get("classified_files", []):
        try:
            sha = _sha256(Path(item["original_path"]))
            hashed.append(
                {
                    **item,
                    "sha256": sha,
                    "asset_id": sha[:16],
                }
            )
        except Exception as exc:
            hashed.append({**item, "sha256": None, "asset_id": None, "hash_error": str(exc)})
    return {**state, "hashed_files": hashed}


# ── Node: deduplicate ─────────────────────────────────────────────────────────

def deduplicate(state: IngestState) -> IngestState:
    """Flag files that are duplicates of an already-seen SHA-256 in this batch."""
    seen: dict[str, str] = {}  # sha256 -> asset_id of first occurrence
    deduplicated: list[dict] = []

    for item in state.get("hashed_files", []):
        sha = item.get("sha256")
        if not sha:
            deduplicated.append({**item, "is_duplicate": False, "duplicate_of": None})
            continue
        if sha in seen:
            deduplicated.append(
                {**item, "is_duplicate": True, "duplicate_of": seen[sha]}
            )
        else:
            seen[sha] = item["asset_id"]
            deduplicated.append({**item, "is_duplicate": False, "duplicate_of": None})

    return {**state, "deduplicated": deduplicated}


# ── Node: copy_assets ─────────────────────────────────────────────────────────

def copy_assets(state: IngestState) -> IngestState:
    """Copy each non-duplicate asset to its destination under data/inputs/."""
    if state.get("dry_run"):
        # In dry-run mode just fill in the would-be destination path
        copied: list[dict] = []
        for item in state.get("deduplicated", []):
            mc = item.get("media_class", "unknown")
            dest_dir = _INPUTS_ROOT / (mc + "s") / state["collection"]
            dest = dest_dir / item["filename"]
            copied.append({**item, "ingested_path": str(dest), "copy_status": "dry_run"})
        return {**state, "copied_files": copied}

    copied = []
    errors: list[str] = list(state.get("errors", []))

    for item in state.get("deduplicated", []):
        mc = item.get("media_class", "unknown")
        dest_dir = _INPUTS_ROOT / (mc + "s") / state["collection"]
        dest = dest_dir / item["filename"]

        if item.get("is_duplicate"):
            copied.append({**item, "ingested_path": str(dest), "copy_status": "skipped_duplicate"})
            continue

        if dest.exists():
            # If SHA matches, skip — already ingested
            try:
                existing_sha = _sha256(dest)
                if existing_sha == item.get("sha256"):
                    copied.append(
                        {**item, "ingested_path": str(dest), "copy_status": "already_exists"}
                    )
                    continue
            except Exception:
                pass

        try:
            copy_asset(item["original_path"], dest)
            copied.append({**item, "ingested_path": str(dest), "copy_status": "copied"})
        except Exception as exc:
            errors.append(f"Failed to copy {item['original_path']}: {exc}")
            copied.append({**item, "ingested_path": str(dest), "copy_status": "error"})

    return {**state, "copied_files": copied, "errors": errors}


# ── Node: register ────────────────────────────────────────────────────────────

def register(state: IngestState) -> IngestState:
    """Upsert all assets into the SQLite registry."""
    now = datetime.now(UTC)
    errors: list[str] = list(state.get("errors", []))

    with get_connection(_DB_PATH) as conn:
        for item in state.get("copied_files", []):
            if not item.get("sha256"):
                continue
            try:
                # Check if already registered
                existing = conn.execute(
                    select(assets.c.id).where(assets.c.sha256 == item["sha256"])
                ).fetchone()

                row = {
                    "id": item["asset_id"],
                    "sha256": item["sha256"],
                    "filename": item["filename"],
                    "original_path": item["original_path"],
                    "ingested_path": item.get("ingested_path"),
                    "size_bytes": item["size_bytes"],
                    "mime_type": item.get("mime_type"),
                    "extension": item.get("extension"),
                    "media_class": item.get("media_class", "unknown"),
                    "collection": state["collection"],
                    "ingested_at": now,
                    "is_duplicate": item.get("is_duplicate", False),
                    "duplicate_of": item.get("duplicate_of"),
                    "status": "ingested",
                }

                if existing is None:
                    conn.execute(insert(assets).values(**row))
                # Skip re-registration of already-known assets

            except Exception as exc:
                errors.append(f"DB error for {item.get('filename')}: {exc}")

        # Query the actual registered count for this collection from the DB
        row_count = conn.execute(
            select(func.count()).select_from(assets).where(
                assets.c.collection == state["collection"]
            )
        ).scalar() or 0

    return {**state, "registered_count": int(row_count), "errors": errors}
