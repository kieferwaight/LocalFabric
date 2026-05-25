"""One-off intelligence pass: enumerate files + every YAML `id:` in this subtree."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "analysis.jsonl"


def tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "--", "."],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def harvest_ids(rel_path: str) -> list[tuple[str, str]]:
    """Return (id, kind) for every `id:` field reachable in the YAML doc."""
    found: list[tuple[str, str]] = []
    abs_path = ROOT / rel_path
    try:
        text = abs_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return found
    try:
        docs = list(yaml.safe_load_all(text))
    except yaml.YAMLError:
        return found

    def walk(node, kind_hint: str) -> None:
        if isinstance(node, dict):
            if "id" in node and isinstance(node["id"], str):
                found.append((node["id"], kind_hint))
            for k, v in node.items():
                walk(v, k if isinstance(k, str) else kind_hint)
        elif isinstance(node, list):
            for item in node:
                walk(item, kind_hint)

    for doc in docs:
        walk(doc, "definition")
    return found


def main() -> None:
    files = tracked_files()
    lines: list[str] = []

    for rel in files:
        lines.append(json.dumps({"id": rel, "type": "file"}, sort_keys=True))

    for rel in files:
        if not rel.endswith((".yaml", ".yml")):
            continue
        for ident, kind in harvest_ids(rel):
            lines.append(
                json.dumps(
                    {"id": ident, "file": rel, "type": kind},
                    sort_keys=True,
                )
            )

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {len(lines)} records to {OUT}")


if __name__ == "__main__":
    main()
