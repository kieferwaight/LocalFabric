"""Workspace path constants and predicate helpers.

``WORKSPACES_ROOT`` is the single canonical anchor that every other module
uses to locate buckets (09_services, 14_data, etc.). Override via the
``WORKSPACES_ROOT`` env var if you need to point at a different tree
(e.g. for tests).
"""

from __future__ import annotations

import os
from pathlib import Path

from core.config import get_settings


def _resolve_workspaces_root() -> Path:
    """Resolve the 20_workspaces directory.

    Honours ``WORKSPACES_ROOT`` env var; otherwise derived from this module's
    file location (``02_core/src/core/paths.py`` → ``20_workspaces``).
    """
    env_root = os.environ.get("WORKSPACES_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()
    return Path(__file__).resolve().parents[3]


WORKSPACES_ROOT: Path = _resolve_workspaces_root()


def data(*parts: str) -> Path:
    """Path under ``14_data/``."""
    return WORKSPACES_ROOT.joinpath("14_data", *parts)


def stores(*parts: str) -> Path:
    """Path under ``14_data/stores/``."""
    return data("stores", *parts)


def services_dir() -> Path:
    """Path to ``09_services/``."""
    return WORKSPACES_ROOT / "09_services"


def registry_file(name: str) -> Path:
    """Path to a file under ``14_data/_registry/`` (e.g. ``services.yaml``)."""
    return data("_registry", name)


# ── Legacy predicates kept for callers in tools/classify and scripts ─────────

_SETTINGS = get_settings()


def is_excluded_dir_name(name: str) -> bool:
    """Return True when *name* is an always-excluded directory segment."""
    lname = name.lower()
    return lname in {d.lower() for d in _SETTINGS.ignored_dir_names}


def is_protected_inbox_path(rel_path: Path) -> bool:
    """Return True when *rel_path* falls under a protected inbox subpath."""
    posix = rel_path.as_posix().lower()
    for protected in _SETTINGS.protected_inbox_subpaths:
        prefix = protected.lower().rstrip("/")
        if posix == prefix or posix.startswith(prefix + "/"):
            return True
    return False
