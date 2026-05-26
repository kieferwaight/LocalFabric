"""Repository environment — paths and runtime-mode flags.

Re-exports the canonical path resolvers (``REPO_ROOT``, ``data``,
``stores``, ``services_dir``, ``registry_file``) and the runtime-mode
helpers (``mode``, ``log_level``, ``dry_run``, ``offline``) so both live
behind one import surface: ``from core.environment import REPO_ROOT,
data, dry_run``.
"""

from __future__ import annotations

from .paths import REPO_ROOT, data, registry_file, services_dir, stores
from .runtime_mode import dry_run, log_level, mode, offline

__all__ = [
    "REPO_ROOT",
    "data",
    "stores",
    "services_dir",
    "registry_file",
    "mode",
    "log_level",
    "dry_run",
    "offline",
]
