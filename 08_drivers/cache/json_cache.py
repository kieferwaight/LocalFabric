"""Small JSON-file cache driver for filesystem-backed tool state."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class JsonCache:
    """Persist a JSON object at a configured filesystem path."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser()

    def load(self) -> dict[str, Any]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            return {}
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (json.JSONDecodeError, OSError):
            return {}

    def write(self, value: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    def clear(self) -> None:
        if self.path.exists():
            self.path.unlink()
