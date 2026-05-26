"""File-walking and hashing helpers used by classification/ingest scripts."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from pathlib import Path

from core.environment import REPO_ROOT

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}

IGNORED_DIR_NAMES: frozenset[str] = frozenset({".git", "node_modules", "__pycache__"})
IGNORED_FILE_NAMES: frozenset[str] = frozenset({".DS_Store"})
EXCLUDED_PREFIXES: tuple[str, ...] = ("20_backups", "20_Backups")
PROTECTED_INBOX_SUBPATHS: tuple[str, ...] = (
    "00_inbox/business",
    "00_inbox/misc",
    "00_inbox/personal",
    "00_inbox/resume",
    "00_inbox/resumes",
)


def _is_protected_inbox(rel: Path) -> bool:
    posix = rel.as_posix().lower()
    for protected in PROTECTED_INBOX_SUBPATHS:
        prefix = protected.lower().rstrip("/")
        if posix == prefix or posix.startswith(prefix + "/"):
            return True
    return False


def iter_files(root: Path = REPO_ROOT) -> Iterable[Path]:
    """Yield files under *root*, skipping excluded dirs, protected inboxes, and backups."""
    excluded_lower = {p.lower() for p in EXCLUDED_PREFIXES}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.name in IGNORED_FILE_NAMES:
            continue

        rel = path.relative_to(root)
        if any(part.lower() in IGNORED_DIR_NAMES for part in rel.parts[:-1]):
            continue
        if _is_protected_inbox(rel):
            continue

        rel_str = rel.as_posix().lower()
        if any(rel_str.startswith(prefix) for prefix in excluded_lower):
            continue

        yield path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
