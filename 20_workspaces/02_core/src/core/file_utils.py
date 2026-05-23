from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable

from core.config import get_settings
from core.paths import ROOT, is_excluded_dir_name, is_protected_inbox_path

SETTINGS = get_settings()
_FULLY_EXCLUDED = tuple(p.lower() for p in SETTINGS.fully_excluded_prefixes)


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


def iter_files(root: Path = ROOT) -> Iterable[Path]:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.name in SETTINGS.ignored_file_names:
            continue

        rel = path.relative_to(root)
        rel_parts = [p.lower() for p in rel.parts]

        if any(is_excluded_dir_name(part) for part in rel_parts[:-1]):
            continue

        if is_protected_inbox_path(rel):
            continue

        # Never touch backup directories
        rel_str = rel.as_posix()
        if any(rel_str.lower().startswith(prefix.lower()) for prefix in SETTINGS.fully_excluded_prefixes):
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
