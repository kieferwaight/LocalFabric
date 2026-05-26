"""SQLAlchemy Core table definitions for the asset registry."""

from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    Text,
)

metadata = MetaData()

# ── Asset Registry ────────────────────────────────────────────────────────────

assets = Table(
    "assets",
    metadata,
    Column("id", String(16), primary_key=True),  # first 16 hex chars of sha256
    Column("sha256", String(64), unique=True, nullable=False),
    Column("filename", String, nullable=False),
    Column("original_path", Text, nullable=False),
    Column("ingested_path", Text, nullable=True),  # null when dry_run=True
    Column("size_bytes", Integer, nullable=False),
    Column("mime_type", String(64), nullable=True),
    Column("extension", String(16), nullable=True),
    Column("media_class", String(16), nullable=False),  # image | document | unknown
    Column("collection", String(128), nullable=False),
    Column("ingested_at", DateTime, nullable=False),
    Column("is_duplicate", Boolean, default=False, nullable=False),
    Column("duplicate_of", String(16), nullable=True),  # asset_id of canonical asset
    Column("status", String(32), default="ingested", nullable=False),
)

# ── Workflow Run Log ──────────────────────────────────────────────────────────

workflow_runs = Table(
    "workflow_runs",
    metadata,
    Column("id", String(36), primary_key=True),  # UUID
    Column("workflow_name", String(128), nullable=False),
    Column("asset_id", String(16), nullable=True),
    Column("collection", String(128), nullable=True),
    Column("started_at", DateTime, nullable=False),
    Column("completed_at", DateTime, nullable=True),
    Column("status", String(32), nullable=False),  # running | success | failed
    Column("output_path", Text, nullable=True),
    Column("error", Text, nullable=True),
    Column("metadata_json", Text, nullable=True),  # arbitrary run metadata (JSON)
)
