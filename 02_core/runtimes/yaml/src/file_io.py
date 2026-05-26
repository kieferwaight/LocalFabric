"""Filesystem helpers used by artifact-producing operations."""

from __future__ import annotations

from pathlib import Path


def write_text_artifact(path: str | Path, value: str) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(value, encoding="utf-8")
    return target


def create_artifact_directory(path: str | Path) -> Path:
    target = Path(path)
    target.mkdir(parents=True, exist_ok=True)
    return target


def remove_artifact(path: str | Path) -> None:
    target = Path(path)
    if target.exists():
        target.unlink()
