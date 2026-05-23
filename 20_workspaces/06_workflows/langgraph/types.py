"""Shared TypedDict state models for LangGraph workflows."""

from __future__ import annotations

from typing import Any, TypedDict


class IngestState(TypedDict, total=False):
    source_dir: str
    collection: str
    dry_run: bool
    scanned_files: list[dict[str, Any]]
    classified_files: list[dict[str, Any]]
    hashed_files: list[dict[str, Any]]
    deduplicated: list[dict[str, Any]]
    copied_files: list[dict[str, Any]]
    registered_count: int
    errors: list[str]


class ImageIntelligenceState(TypedDict, total=False):
    image_path: str
    asset_id: str | None
    collection: str
    run_id: str
    classification: dict[str, Any] | None
    color: dict[str, Any] | None
    meta: dict[str, Any] | None
    quality: dict[str, Any] | None
    regions: dict[str, Any] | None
    text: dict[str, Any] | None
    vision_overview: str
    vision_layout: str
    vision_style: str
    vision_error: str
    output_path: str | None
    error: str | None
