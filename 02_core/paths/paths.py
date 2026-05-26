"""Repository path constants.

``REPO_ROOT`` is the single canonical anchor that every other module uses to
locate buckets (``09_services``, ``14_data``, …). Override via the ``REPO_ROOT``
env var to point at a different tree (tests use this).
"""

from __future__ import annotations

import os
from pathlib import Path


def _resolve_repo_root() -> Path:
    env_root = os.environ.get("REPO_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()
    # 02_core/paths.py → repo root
    return Path(__file__).resolve().parents[1]


REPO_ROOT: Path = _resolve_repo_root()


def data(*parts: str) -> Path:
    """Path under ``14_data/``."""
    return REPO_ROOT.joinpath("14_data", *parts)


def stores(*parts: str) -> Path:
    """Path under ``14_data/stores/``."""
    return data("stores", *parts)


def services_dir() -> Path:
    """Path to ``09_services/``."""
    return REPO_ROOT / "09_services"


def registry_file(name: str) -> Path:
    """Path to a file under ``14_data/_registry/`` (e.g. ``services.yaml``)."""
    return data("_registry", name)
