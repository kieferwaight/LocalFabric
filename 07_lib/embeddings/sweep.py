"""
sweep.py — Atomic helpers for walking, hashing, and manifesting the embedding sweep.

Public surface:
    collect_files(root)              — walk *root* and return indexable file paths
    file_hash(path)                  — MD5 hex digest of a single file
    load_manifest(manifest_path)     — read the sweep manifest JSON (or return {})
    save_manifest(manifest_path, m)  — write the sweep manifest JSON

The orchestration loop (collect → chunk → embed → upsert → persist manifest) lives
in ``06_workflows/embeddings-sweep.yaml``.
"""

import hashlib
import json
import os

# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------

# Extensions to index (all others skipped)
INDEXED_EXTENSIONS = {
    ".py", ".md", ".txt", ".rst", ".yaml", ".yml",
    ".toml", ".json", ".sh", ".bash", ".env",
}

# Directories to always skip
SKIP_DIRS = {
    ".git", "__pycache__", ".mypy_cache", ".pytest_cache",
    "node_modules", ".venv", "venv", "env", ".tox",
    "*.egg-info", ".DS_Store",
}

# ------------------------------------------------------------------
# Manifest helpers (dirty-check at file level)
# ------------------------------------------------------------------

def load_manifest(manifest_path: str) -> dict[str, str]:
    """Load the sweep manifest from *manifest_path*, returning {} on missing/corrupt."""
    os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_manifest(manifest_path: str, manifest: dict[str, str]) -> None:
    """Persist *manifest* as JSON to *manifest_path*."""
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)


def file_hash(path: str) -> str:
    """Return the MD5 hex digest of the file at *path*."""
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(65536), b""):
            h.update(block)
    return h.hexdigest()


# ------------------------------------------------------------------
# Directory walker
# ------------------------------------------------------------------

def collect_files(root: str) -> list[str]:
    """Return all indexable file paths under *root*, sorted."""
    collected = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Prune skip dirs in-place so os.walk doesn't descend into them
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for fname in filenames:
            ext = os.path.splitext(fname)[1].lower()
            if ext in INDEXED_EXTENSIONS:
                collected.append(os.path.join(dirpath, fname))
    return sorted(collected)
