"""Runtime-mode environment-variable resolvers.

Centralised reads of process-level configuration:

- ``LOCALFABRIC_MODE``  — ``dev`` (default) or ``prod``. Drives anything
  that should differ between local development and a production-like
  deployment.
- ``LOG_LEVEL``         — Python ``logging`` level name (``DEBUG``,
  ``INFO``, ``WARNING``, ``ERROR``). Defaults to ``INFO``.
- ``DRY_RUN``           — When ``1`` / ``true`` / ``yes``, code paths
  that would write to disk, hit the network, or mutate external state
  should short-circuit and just describe what they would have done.
- ``OFFLINE``           — When ``1`` / ``true`` / ``yes``, network egress
  is forbidden; fetchers must refuse instead of attempting a request.

All values are read on every call (no caching) so test harnesses can
mutate the environment between invocations.
"""

from __future__ import annotations

import os

_TRUTHY = frozenset({"1", "true", "yes", "on"})


def _flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in _TRUTHY


def mode() -> str:
    """Return ``LOCALFABRIC_MODE`` lowercased, defaulting to ``dev``."""
    return os.environ.get("LOCALFABRIC_MODE", "dev").strip().lower()


def log_level() -> str:
    """Return ``LOG_LEVEL`` uppercased, defaulting to ``INFO``."""
    return os.environ.get("LOG_LEVEL", "INFO").strip().upper()


def dry_run() -> bool:
    """``True`` when ``DRY_RUN`` is set to a truthy value."""
    return _flag("DRY_RUN")


def offline() -> bool:
    """``True`` when ``OFFLINE`` is set to a truthy value."""
    return _flag("OFFLINE")
