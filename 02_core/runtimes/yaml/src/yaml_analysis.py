"""Pure-Python analysis + mutation over the YAML definition graph.

Definitions live as top-level list items in YAML files; the runtime resolves
references through `extends`, `mixins`, `modules`, nested `render`/`invoke`
blocks, and Jinja `component('<id>', ...)` calls inside string values.
This module enumerates them all, finds broken refs, and rewrites ids in place.
"""
from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Iterator

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent

__all__ = [
    "Relationship",
    "IdOccurrence",
    "discover_yaml_files",
    "list_tracked_files",
    "list_definitions",
    "list_id_relationships",
    "list_module_includes",
    "list_all_id_occurrences",
    "list_broken_relationships",
    "list_broken_module_includes",
    "assert_no_broken_references",
    "snapshot",
    "write_snapshot",
    "update_id",
    "update_module_paths",
]

# Jinja component('id', ...) calls embedded in string values.
# Backtick lookbehind avoids matching `component('foo')` shown as prose example.
COMPONENT_CALL = re.compile(r"""(?<!`)component\(\s*['"]([^'"]+)['"]""")

# Top-level definition keys that hold a single id reference.
SINGLE_ID_KEYS = ("extends",)
# Top-level definition keys that hold a list of id references.
LIST_ID_KEYS = ("mixins",)
# Nested operation keys (under `run:`) that target a definition id.
INVOKE_OP_KEYS = ("render", "invoke")
# Runtime-injected globals that look like references but aren't.
RUNTIME_GLOBALS = ("runtime.catalog.definitions", "runtime.catalog.tags",
                   "runtime.catalog.generated_marker")


@dataclass(frozen=True)
class Relationship:
    source_id: str
    target_id: str
    kind: str            # "extends" | "mixin" | "invoke" | "render" | "component" | "module"
    source_file: str

    def as_dict(self) -> dict[str, str]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "kind": self.kind,
            "source_file": self.source_file,
        }


@dataclass
class Definition:
    id: str
    file: str
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class IdOccurrence:
    """An `id:` field encountered anywhere in a YAML doc, not just top-level."""
    id: str
    file: str
    parent_key: str  # "definition" for top-level list items, else the enclosing key


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def _git_ls_files(root: Path) -> list[str]:
    """Tracked + untracked paths under `root`, honoring .gitignore."""
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "--", "."],
        cwd=root, check=True, capture_output=True, text=True,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def list_tracked_files(root: Path = REPO_ROOT) -> list[str]:
    """Every tracked + untracked file path relative to `root` (all extensions)."""
    return [line for line in _git_ls_files(root) if (root / line).exists()]


def discover_yaml_files(root: Path = REPO_ROOT) -> list[Path]:
    """Tracked + untracked YAML files honoring .gitignore."""
    return [
        root / line for line in _git_ls_files(root)
        if line.endswith((".yaml", ".yml")) and (root / line).exists()
    ]


def load_yaml(path: Path) -> list[dict[str, Any]]:
    """Return top-level list items, skipping non-dict entries."""
    text = path.read_text(encoding="utf-8")
    docs = list(yaml.safe_load_all(text))
    items: list[dict[str, Any]] = []
    for doc in docs:
        if isinstance(doc, list):
            items.extend(d for d in doc if isinstance(d, dict))
        elif isinstance(doc, dict):
            items.append(doc)
    return items


def list_definitions(root: Path = REPO_ROOT) -> list[Definition]:
    out: list[Definition] = []
    for path in discover_yaml_files(root):
        rel = path.relative_to(root).as_posix()
        for entry in load_yaml(path):
            ident = entry.get("id")
            if isinstance(ident, str):
                out.append(Definition(id=ident, file=rel, raw=entry))
    return out


# ---------------------------------------------------------------------------
# Reference extraction
# ---------------------------------------------------------------------------

def _walk_strings(node: Any) -> Iterator[str]:
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for v in node.values():
            yield from _walk_strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from _walk_strings(v)


def _walk_invoke_targets(node: Any) -> Iterator[tuple[str, str]]:
    """Yield (kind, target_id) for nested render:/invoke: blocks under run:."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k in INVOKE_OP_KEYS and isinstance(v, dict):
                target = v.get("definition")
                if isinstance(target, str) and "{{" not in target:
                    yield k, target
            yield from _walk_invoke_targets(v)
    elif isinstance(node, list):
        for v in node:
            yield from _walk_invoke_targets(v)


def extract_references(definition: Definition) -> list[Relationship]:
    out: list[Relationship] = []
    raw, src_id, src_file = definition.raw, definition.id, definition.file

    for key in SINGLE_ID_KEYS:
        ref = raw.get(key)
        if isinstance(ref, str):
            out.append(Relationship(src_id, ref, key, src_file))

    for key in LIST_ID_KEYS:
        refs = raw.get(key)
        if isinstance(refs, list):
            for ref in refs:
                if isinstance(ref, str):
                    out.append(Relationship(src_id, ref, "mixin", src_file))

    run = raw.get("run")
    if isinstance(run, list):
        for kind, target in _walk_invoke_targets(run):
            out.append(Relationship(src_id, target, kind, src_file))

    for s in _walk_strings(raw):
        for m in COMPONENT_CALL.finditer(s):
            out.append(Relationship(src_id, m.group(1), "component", src_file))

    return out


def extract_module_includes(definition: Definition) -> list[str]:
    """Filenames in `modules:` are file references, not id references."""
    mods = definition.raw.get("modules")
    if not isinstance(mods, list):
        return []
    return [m for m in mods if isinstance(m, str)]


# ---------------------------------------------------------------------------
# Relationship listing
# ---------------------------------------------------------------------------

def list_id_relationships(root: Path = REPO_ROOT) -> list[Relationship]:
    out: list[Relationship] = []
    for d in list_definitions(root):
        out.extend(extract_references(d))
    return out


def list_broken_relationships(root: Path = REPO_ROOT) -> list[Relationship]:
    defs = list_definitions(root)
    known = {d.id for d in defs}
    return [
        r for r in list_id_relationships(root)
        if r.target_id not in known and r.target_id not in RUNTIME_GLOBALS
    ]


def list_module_includes(root: Path = REPO_ROOT) -> list[tuple[str, str, str]]:
    """Return (source_id, included_filename, source_file)."""
    out: list[tuple[str, str, str]] = []
    for d in list_definitions(root):
        for inc in extract_module_includes(d):
            out.append((d.id, inc, d.file))
    return out


def list_broken_module_includes(root: Path = REPO_ROOT) -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []
    for src_id, inc, src_file in list_module_includes(root):
        resolved = (root / src_file).parent / inc
        if not resolved.exists():
            out.append((src_id, inc, src_file))
    return out


# ---------------------------------------------------------------------------
# Snapshot — combined file + id occurrence stream
# ---------------------------------------------------------------------------

def _walk_id_occurrences(
    node: Any, file_rel: str, parent_key: str
) -> Iterator[IdOccurrence]:
    if isinstance(node, dict):
        ident = node.get("id")
        if isinstance(ident, str):
            yield IdOccurrence(id=ident, file=file_rel, parent_key=parent_key)
        for key, value in node.items():
            yield from _walk_id_occurrences(value, file_rel, key if isinstance(key, str) else parent_key)
    elif isinstance(node, list):
        for item in node:
            yield from _walk_id_occurrences(item, file_rel, parent_key)


def list_all_id_occurrences(root: Path = REPO_ROOT) -> list[IdOccurrence]:
    """Every `id:` field at any depth, keyed by its enclosing dict key.

    Top-level list items are reported as `parent_key="definition"`; nested ids
    (e.g. inside `docs:`, `modules:` entries) carry their actual parent key.
    """
    out: list[IdOccurrence] = []
    for path in discover_yaml_files(root):
        rel = path.relative_to(root).as_posix()
        try:
            docs = list(yaml.safe_load_all(path.read_text(encoding="utf-8")))
        except yaml.YAMLError:
            continue
        for doc in docs:
            out.extend(_walk_id_occurrences(doc, rel, "definition"))
    return out


def snapshot(root: Path = REPO_ROOT) -> list[dict[str, Any]]:
    """File index + every id occurrence — JSONL-ready records.

    Two record shapes:
      - `{"id": <path>, "type": "file"}` — one per tracked/untracked file.
      - `{"id": <ident>, "file": <path>, "type": <parent_key>}` — one per id.
    """
    records: list[dict[str, Any]] = [
        {"id": rel, "type": "file"} for rel in list_tracked_files(root)
    ]
    records.extend(
        {"id": occ.id, "file": occ.file, "type": occ.parent_key}
        for occ in list_all_id_occurrences(root)
    )
    return records


def write_snapshot(output_path: Path, root: Path = REPO_ROOT) -> int:
    """Write `snapshot(root)` as JSONL. Returns the record count."""
    records = snapshot(root)
    lines = [json.dumps(r, sort_keys=True) for r in records]
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(records)


# ---------------------------------------------------------------------------
# Verification — pre-runtime / runtime safety net
# ---------------------------------------------------------------------------

def assert_no_broken_references(root: Path = REPO_ROOT) -> None:
    """Raise `RuntimeError` if any id or module include fails to resolve."""
    broken_ids = list_broken_relationships(root)
    broken_modules = list_broken_module_includes(root)
    if not broken_ids and not broken_modules:
        return
    lines: list[str] = []
    if broken_ids:
        lines.append(f"{len(broken_ids)} broken id reference(s):")
        for rel in broken_ids:
            lines.append(
                f"  {rel.source_id} --{rel.kind}--> {rel.target_id}  ({rel.source_file})"
            )
    if broken_modules:
        lines.append(f"{len(broken_modules)} broken module include(s):")
        for src_id, inc, src_file in broken_modules:
            lines.append(f"  {src_id} --module--> {inc}  ({src_file})")
    raise RuntimeError("\n".join(lines))


# ---------------------------------------------------------------------------
# Mutation
# ---------------------------------------------------------------------------

def _rewrite_text_ids(text: str, mapping: dict[str, str]) -> str:
    """Rewrite ids in YAML source while preserving formatting.

    We operate on YAML source text rather than re-emitting the parsed dict
    so comments, anchors, key order, and string styles survive untouched.
    """
    new = text
    # Sort longest first so prefix-overlapping ids don't clobber each other.
    for old in sorted(mapping, key=len, reverse=True):
        new_id = mapping[old]
        if old == new_id:
            continue
        old_re = re.escape(old)

        # `id: <old>` and `id: "<old>"` etc — value position on any indent.
        new = re.sub(
            rf"(?m)^(\s*-?\s*(?:id|extends|definition)\s*:\s*)({old_re})(\s*(?:#.*)?)$",
            lambda m: f"{m.group(1)}{new_id}{m.group(3)}",
            new,
        )
        new = re.sub(
            rf"""(?m)^(\s*-?\s*(?:id|extends|definition)\s*:\s*)(['"]){old_re}\2(\s*(?:#.*)?)$""",
            lambda m: f"{m.group(1)}{m.group(2)}{new_id}{m.group(2)}{m.group(3)}",
            new,
        )

        # `- <old>` in a YAML list — used by mixins:.
        new = re.sub(
            rf"(?m)^(\s*-\s*)({old_re})(\s*(?:#.*)?)$",
            lambda m: f"{m.group(1)}{new_id}{m.group(3)}",
            new,
        )
        new = re.sub(
            rf"""(?m)^(\s*-\s*)(['"]){old_re}\2(\s*(?:#.*)?)$""",
            lambda m: f"{m.group(1)}{m.group(2)}{new_id}{m.group(2)}{m.group(3)}",
            new,
        )

        # Jinja component('<old>', ...) calls.
        new = re.sub(
            rf"""(component\(\s*)(['"]){old_re}\2""",
            lambda m: f"{m.group(1)}{m.group(2)}{new_id}{m.group(2)}",
            new,
        )

    return new


def update_id(mapping: dict[str, str], root: Path = REPO_ROOT) -> dict[str, int]:
    """Rename ids and propagate through every reference site. Returns per-file change counts."""
    changes: dict[str, int] = {}
    for path in discover_yaml_files(root):
        text = path.read_text(encoding="utf-8")
        new = _rewrite_text_ids(text, mapping)
        if new != text:
            path.write_text(new, encoding="utf-8")
            changes[path.relative_to(root).as_posix()] = sum(
                1 for old in mapping if old in text and mapping[old] != old
            )
    return changes


def update_module_paths(mapping: dict[str, str], root: Path = REPO_ROOT) -> dict[str, int]:
    """Rewrite filenames inside `modules:` lists. Paths are relative to the YAML they appear in."""
    changes: dict[str, int] = {}
    for path in discover_yaml_files(root):
        text = path.read_text(encoding="utf-8")
        new = text
        for old, new_path in mapping.items():
            if old == new_path:
                continue
            old_re = re.escape(old)
            new = re.sub(
                rf"(?m)^(\s*-\s*)({old_re})(\s*(?:#.*)?)$",
                lambda m: f"{m.group(1)}{new_path}{m.group(3)}",
                new,
            )
        if new != text:
            path.write_text(new, encoding="utf-8")
            changes[path.relative_to(root).as_posix()] = 1
    return changes


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _print_jsonl(rows: Iterable[dict[str, Any]]) -> None:
    for row in rows:
        print(json.dumps(row, sort_keys=True))


def _cli() -> None:
    import argparse

    p = argparse.ArgumentParser(description="YAML definition-graph analysis")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("definitions", help="List every definition id")
    sub.add_parser("relationships", help="List every id relationship")
    sub.add_parser("broken", help="List broken relationships")
    sub.add_parser("modules", help="List every module include")
    sub.add_parser("broken-modules", help="List module includes whose file is missing")
    sub.add_parser("all-ids", help="List every id occurrence at any depth")
    snap = sub.add_parser("snapshot", help="Write file + id JSONL snapshot")
    snap.add_argument("--output", default="analysis.jsonl",
                      help="Output path (default: analysis.jsonl)")
    sub.add_parser("verify", help="Exit nonzero if any reference is broken")

    args = p.parse_args()
    root = REPO_ROOT

    if args.cmd == "definitions":
        _print_jsonl({"id": d.id, "file": d.file} for d in list_definitions(root))
    elif args.cmd == "relationships":
        _print_jsonl(r.as_dict() for r in list_id_relationships(root))
    elif args.cmd == "broken":
        _print_jsonl(r.as_dict() for r in list_broken_relationships(root))
    elif args.cmd == "modules":
        _print_jsonl(
            {"source_id": s, "module": m, "source_file": f}
            for s, m, f in list_module_includes(root)
        )
    elif args.cmd == "broken-modules":
        _print_jsonl(
            {"source_id": s, "module": m, "source_file": f}
            for s, m, f in list_broken_module_includes(root)
        )
    elif args.cmd == "all-ids":
        _print_jsonl(
            {"id": occ.id, "file": occ.file, "type": occ.parent_key}
            for occ in list_all_id_occurrences(root)
        )
    elif args.cmd == "snapshot":
        out = Path(args.output)
        if not out.is_absolute():
            out = root / out
        count = write_snapshot(out, root)
        print(f"wrote {count} records to {out}")
    elif args.cmd == "verify":
        import sys as _sys
        try:
            assert_no_broken_references(root)
        except RuntimeError as exc:
            _sys.stderr.write(f"{exc}\n")
            _sys.exit(1)
        print("OK: zero broken references")


if __name__ == "__main__":
    _cli()
