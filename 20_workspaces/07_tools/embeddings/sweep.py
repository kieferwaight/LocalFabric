"""
sweep.py — Walk the project directory, chunk + embed all files, persist to LanceDB.

Only re-embeds files whose content has changed since the last sweep (MD5 dirty-check
is handled by Embedder's cache; this script adds a per-file hash manifest so unchanged
files are skipped at the file level before any chunking happens).

Usage:
    python -m tools.embeddings.sweep                       # sweep default project root
    python -m tools.embeddings.sweep /path/to/target/dir   # sweep a custom directory
    python -m tools.embeddings.sweep --dry-run             # print what would be swept, don't embed
    python -m tools.embeddings.sweep --force               # re-embed all files regardless of changes
    python -m tools.embeddings.sweep --clear               # drop and rebuild the entire store
"""

import argparse
import hashlib
import json
import os
import sys
import time

# Allow running as a script. The new layout places this file at
# 20_workspaces/07_tools/embeddings/sweep.py, while the importable packages
# ``tools`` and ``drivers`` live two levels up under 20_workspaces/. Walk up
# accordingly so ``python sweep.py`` works without an explicit PYTHONPATH.
_WORKSPACES_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
if _WORKSPACES_ROOT not in sys.path:
    sys.path.insert(0, _WORKSPACES_ROOT)

from tools.embeddings.chunker import chunk_file
from tools.embeddings.embedder import Embedder, EmbedderUnavailable
from drivers.vector.lancedb_driver import LanceStore

# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------

_DEFAULT_TARGET = _WORKSPACES_ROOT
_MANIFEST_PATH = os.path.join(
    _WORKSPACES_ROOT, "14_data", "cache", "embeddings", "sweep_manifest.json"
)

# Extensions to index (all others skipped)
INDEXED_EXTENSIONS = {
    ".py", ".md", ".txt", ".rst", ".yaml", ".yml",
    ".toml", ".json", ".sh", ".bash", ".env",
}

# Directories to always skip
SKIP_DIRS = {
    ".git", "__pycache__", ".mypy_cache", ".pytest_cache",
    "node_modules", ".venv", "venv", "env", ".tox",
    "ai_utils.egg-info", ".DS_Store",
}

# ------------------------------------------------------------------
# File manifest (dirty-check at file level)
# ------------------------------------------------------------------

def _load_manifest() -> dict[str, str]:
    os.makedirs(os.path.dirname(_MANIFEST_PATH), exist_ok=True)
    if os.path.exists(_MANIFEST_PATH):
        try:
            with open(_MANIFEST_PATH, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_manifest(manifest: dict[str, str]) -> None:
    with open(_MANIFEST_PATH, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)


def _file_hash(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(65536), b""):
            h.update(block)
    return h.hexdigest()


# ------------------------------------------------------------------
# Directory walker
# ------------------------------------------------------------------

def _collect_files(root: str) -> list[str]:
    """Return all indexable file paths under *root*."""
    collected = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Prune skip dirs in-place so os.walk doesn't descend into them
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for fname in filenames:
            ext = os.path.splitext(fname)[1].lower()
            if ext in INDEXED_EXTENSIONS:
                collected.append(os.path.join(dirpath, fname))
    return sorted(collected)


# ------------------------------------------------------------------
# Main sweep
# ------------------------------------------------------------------

def sweep(
    target_dir: str = _DEFAULT_TARGET,
    dry_run: bool = False,
    force: bool = False,
    clear: bool = False,
    verbose: bool = False,
) -> dict:
    """
    Sweep *target_dir* and embed all changed files into the LanceDB store.

    Returns a summary dict:
        {files_scanned, files_changed, chunks_added, skipped, errors, elapsed_sec}
    """
    t0 = time.time()
    print(f"[Sweep] Target: {target_dir}")
    print(f"[Sweep] Mode: {'dry-run' if dry_run else 'live'}"
          + (" | force-reindex" if force else "")
          + (" | clear-store" if clear else ""))

    store = LanceStore()
    embedder = Embedder()
    manifest = _load_manifest()

    if clear and not dry_run:
        store.clear()
        manifest = {}
        print("[Sweep] Store cleared.")

    files = _collect_files(target_dir)
    print(f"[Sweep] Found {len(files)} indexable files.")

    stats = {
        "files_scanned": len(files),
        "files_changed": 0,
        "chunks_added": 0,
        "skipped": 0,
        "errors": 0,
        "elapsed_sec": 0.0,
    }

    for path in files:
        try:
            fhash = _file_hash(path)
        except OSError as exc:
            print(f"[Sweep] ERROR reading {path}: {exc}")
            stats["errors"] += 1
            continue

        rel = os.path.relpath(path, target_dir)

        # Skip if unchanged (unless force)
        if not force and manifest.get(path) == fhash:
            stats["skipped"] += 1
            if verbose:
                print(f"[Sweep] SKIP (unchanged): {rel}")
            continue

        stats["files_changed"] += 1
        print(f"[Sweep] Processing: {rel}")

        if dry_run:
            chunks = chunk_file(path)
            print(f"  → would embed {len(chunks)} chunks")
            continue

        # Chunk
        chunks = chunk_file(path)
        if not chunks:
            manifest[path] = fhash
            continue

        # Remove old chunks for this file before re-adding
        if manifest.get(path):
            store.delete_source(os.path.abspath(path))

        # Embed
        try:
            chunks = embedder.embed_chunks(chunks, verbose=verbose)
        except EmbedderUnavailable as exc:
            print(f"[Sweep] ABORT — Embedder unavailable: {exc}")
            print("[Sweep] Make sure Ollama is running: ollama serve")
            stats["elapsed_sec"] = time.time() - t0
            return stats

        # Persist
        added = store.add(chunks)
        stats["chunks_added"] += added
        manifest[path] = fhash

        if verbose:
            print(f"  → added {added} chunks")

    if not dry_run:
        _save_manifest(manifest)
        embedder.flush_cache()

    stats["elapsed_sec"] = round(time.time() - t0, 2)
    _print_summary(stats)
    return stats


def _print_summary(stats: dict) -> None:
    print("\n" + "=" * 50)
    print("[Sweep] Summary")
    print(f"  Files scanned : {stats['files_scanned']}")
    print(f"  Files changed : {stats['files_changed']}")
    print(f"  Chunks added  : {stats['chunks_added']}")
    print(f"  Skipped       : {stats['skipped']}")
    print(f"  Errors        : {stats['errors']}")
    print(f"  Elapsed       : {stats['elapsed_sec']}s")
    print("=" * 50)


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sweep and embed project files into LanceDB.")
    parser.add_argument("target", nargs="?", default=_DEFAULT_TARGET, help="Directory to sweep")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be processed without embedding")
    parser.add_argument("--force", action="store_true", help="Re-embed all files regardless of changes")
    parser.add_argument("--clear", action="store_true", help="Drop and rebuild the entire store")
    parser.add_argument("--verbose", action="store_true", help="Print per-chunk progress")
    args = parser.parse_args()

    sweep(
        target_dir=args.target,
        dry_run=args.dry_run,
        force=args.force,
        clear=args.clear,
        verbose=args.verbose,
    )
