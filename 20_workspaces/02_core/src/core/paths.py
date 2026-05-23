"""Repository path constants and predicate helpers.

This module was referenced by the legacy ``ai_utils`` package but was not
present in the migrated source tree. It is recreated here from its callers'
usage to keep ``file_utils`` and ``scripts/classify_files`` functional.
"""

from __future__ import annotations

import os
from pathlib import Path

from core.config import get_settings

_SETTINGS = get_settings()


def _resolve_root() -> Path:
    """Resolve the repository root.

    Honours the ``AI_UTILS_ROOT`` environment variable when set, otherwise
    falls back to the current working directory.
    """
    env_root = os.environ.get("AI_UTILS_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()
    return Path.cwd().resolve()


ROOT: Path = _resolve_root()
MANIFESTS_DIR: Path = ROOT / "manifests"


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
