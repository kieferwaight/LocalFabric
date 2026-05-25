"""PDF-specific metadata extraction utilities."""

from __future__ import annotations

import subprocess
from pathlib import Path


def page_count(path: Path) -> int | None:
    """Return page count using the `pdfinfo` document tool when available."""
    result = subprocess.run(["pdfinfo", str(path)], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        if line.startswith("Pages:"):
            try:
                return int(line.split(":", 1)[1].strip())
            except ValueError:
                return None
    return None
