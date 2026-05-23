"""Persistent filesystem operations for workflow artifacts."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any


def copy_asset(source: str | Path, destination: str | Path) -> Path:
    """Copy an input asset into its persistent target directory."""
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return target


def write_json_artifact(path: str | Path, value: dict[str, Any]) -> Path:
    """Write a structured workflow artifact as formatted JSON."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def write_text_artifact(path: str | Path, value: str) -> Path:
    """Write a text artifact, creating its destination directory as needed."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(value, encoding="utf-8")
    return target
