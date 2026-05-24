"""One-shot migration: rename ids, merge sibling files, move into new layout.

Run once with the project venv:
    /Users/kwaight/scratch/20_workspaces/.venv/bin/python _migrate.py

After completion the script can be deleted; the analysis tool lives at
src/yaml_analysis.py and exposes the same primitives via the CLI.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from yaml_analysis import (  # noqa: E402
    discover_yaml_files,
    list_broken_relationships,
    update_id,
    update_module_paths,
)

# ---- 1. Definition-id rename map --------------------------------------------
ID_MAP: dict[str, str] = {
    # stdlib core
    "abstract/base": "stdlib.base",
    "builtin/load-modules": "stdlib.load-modules",
    "builtin/run-command": "stdlib.run-command",
    "builtin/clean-workspace": "stdlib.clean-workspace",
    "builtin/logger": "stdlib.logger",
    # stdlib files
    "builtin/files/write-text": "stdlib.files.write-text",
    "builtin/files/create-directory": "stdlib.files.create-directory",
    # stdlib git
    "builtin/git/init-current-workspace": "stdlib.git.init-current-workspace",
    "builtin/git/gitignore-python": "stdlib.git.gitignore-python",
    "builtin/git/create-github-repository": "stdlib.git.create-github-repository",
    # stdlib docs
    "builtin/docs/prune-definition-pages": "stdlib.docs.prune-definition-pages",
    # docs templates (will merge into one file)
    "docs/templates/index": "docs.definition.template.index",
    "docs/templates/schema": "docs.definition.template.schema",
    "docs/templates/definition": "docs.definition.template.definition",
    "docs/templates/component-relationship-graph": "docs.definition.template.component-relationship-graph",
    # docs catalog + reference (split from config.yaml)
    "docs/catalog/modules": "docs.catalog.modules",
    "docs/api/reference": "docs.api.reference",
    # examples catalog
    "examples/catalog/modules": "examples.catalog.modules",
    # git compositions
    "example/git/init": "git.init",
    "example/git/github": "git.github",
    "example/git/gitignore": "git.gitignore",
    # obsidian
    "example/obsidian-template": "obsidian.template",
    # cloud deployer + its mixins
    "mixin/git-info": "cloud.mixin.git-info",
    "mixin/timestamp": "cloud.mixin.timestamp",
    "cloud/deployer": "cloud.deployer",
}


# ---- 2. File move/merge plan ------------------------------------------------
# Single moves: old path -> new path
SINGLE_MOVES: dict[str, str] = {
    "stdlib/stdlib.yaml": "definitions/stdlib.yaml",
    "stdlib/stdlib.files.yaml": "definitions/stdlib.files.yaml",
    "stdlib/stdlib.git.yaml": "definitions/stdlib.git.yaml",
    "stdlib/stdlib.doc.yaml": "definitions/stdlib.docs.yaml",
    "examples/examples.yaml": "definitions/examples.catalog.yaml",
    "examples/deploy.yaml": "definitions/cloud.yaml",
    "examples/obsidian-template.yaml": "definitions/obsidian.yaml",
}

# Splits: one old file -> N new files (carved by which ids land where)
SPLITS: dict[str, list[tuple[str, list[str]]]] = {
    "config.yaml": [
        ("definitions/docs.catalog.yaml", ["docs.catalog.modules"]),
        ("definitions/docs.yaml", ["docs.api.reference"]),
    ],
}

# Merges: N old files -> 1 new file (concat in given order)
MERGES: dict[str, list[str]] = {
    "definitions/docs.definition.template.yaml": [
        "templates/doc-component-relationship-graph.yaml",
        "templates/doc-index.yaml",
        "templates/doc-schema.yaml",
        "templates/doc-definition.yaml",
    ],
    "definitions/git.yaml": [
        "examples/git-current-workspace.yaml",
        "examples/gitignore-template.yaml",
    ],
}


# ---- 3. Module-include rename map -------------------------------------------
# Tracks how filename strings inside `modules:` lists must change.
MODULE_MAP: dict[str, str] = {
    # stdlib internal refs (inside definitions/stdlib.yaml, siblings now)
    "stdlib.files.yaml": "stdlib.files.yaml",  # unchanged
    "stdlib.git.yaml": "stdlib.git.yaml",      # unchanged
    "stdlib.doc.yaml": "stdlib.docs.yaml",     # renamed
    # config.yaml's module list — all peers in definitions/
    "templates/doc-component-relationship-graph.yaml": "docs.definition.template.yaml",
    "templates/doc-index.yaml": "docs.definition.template.yaml",
    "templates/doc-schema.yaml": "docs.definition.template.yaml",
    "templates/doc-definition.yaml": "docs.definition.template.yaml",
    "examples/examples.yaml": "examples.catalog.yaml",
    # examples/examples.yaml's module list
    "deploy.yaml": "cloud.yaml",
    "git-current-workspace.yaml": "git.yaml",
    "gitignore-template.yaml": "git.yaml",
    "obsidian-template.yaml": "obsidian.yaml",
}


# ---- Execution helpers ------------------------------------------------------
def section(title: str) -> None:
    bar = "=" * 60
    print(f"\n{bar}\n{title}\n{bar}")


def split_yaml_by_id(src: Path, splits: list[tuple[str, list[str]]]) -> None:
    """Split one YAML file into multiple by definition id."""
    import yaml
    text = src.read_text(encoding="utf-8")
    docs = list(yaml.safe_load_all(text))
    flattened: list[dict] = []
    for doc in docs:
        if isinstance(doc, list):
            flattened.extend(doc)
        elif isinstance(doc, dict):
            flattened.append(doc)
    for dest_rel, keep_ids in splits:
        kept = [d for d in flattened if isinstance(d, dict) and d.get("id") in keep_ids]
        dest = REPO_ROOT / dest_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(
            yaml.dump(kept, sort_keys=False, default_flow_style=False, width=120),
            encoding="utf-8",
        )
        print(f"  split: {src.relative_to(REPO_ROOT)} -> {dest_rel} ({len(kept)} ids)")


def merge_yaml_files(dest_rel: str, sources: list[str]) -> None:
    """Concatenate several YAML files (each a top-level list) into one."""
    dest = REPO_ROOT / dest_rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    parts: list[str] = []
    for src_rel in sources:
        src = REPO_ROOT / src_rel
        if not src.exists():
            print(f"  warn: merge source missing: {src_rel}")
            continue
        text = src.read_text(encoding="utf-8").rstrip("\n") + "\n"
        parts.append(text)
    dest.write_text("\n".join(parts), encoding="utf-8")
    print(f"  merge: {len(sources)} files -> {dest_rel}")


def remove_path(rel: str) -> None:
    p = REPO_ROOT / rel
    if p.exists():
        p.unlink()
        print(f"  remove: {rel}")


def remove_empty_dir(rel: str) -> None:
    p = REPO_ROOT / rel
    if p.exists() and p.is_dir() and not any(p.iterdir()):
        p.rmdir()
        print(f"  rmdir: {rel}")


def main() -> None:
    section("1. Rename ids (in-place, before any moves)")
    changes = update_id(ID_MAP, REPO_ROOT)
    for f, n in sorted(changes.items()):
        print(f"  {f}: {n} id(s) rewritten")

    section("2. Verify no broken relationships post-rename")
    broken = list_broken_relationships(REPO_ROOT)
    if broken:
        print("  ERROR: broken relationships after rename:")
        for r in broken:
            print(f"    {r.source_id} --{r.kind}--> {r.target_id}  ({r.source_file})")
        sys.exit(1)
    print("  OK: zero broken relationships")

    section("3. Split config.yaml")
    for src_rel, splits in SPLITS.items():
        src = REPO_ROOT / src_rel
        if not src.exists():
            continue
        split_yaml_by_id(src, splits)
        src.unlink()
        print(f"  removed source: {src_rel}")

    section("4. Single-file moves into definitions/")
    (REPO_ROOT / "definitions").mkdir(exist_ok=True)
    for old, new in SINGLE_MOVES.items():
        src = REPO_ROOT / old
        dst = REPO_ROOT / new
        if not src.exists():
            print(f"  skip (missing): {old}")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        print(f"  move: {old} -> {new}")

    section("5. Merges (template + git compositions)")
    for dest, sources in MERGES.items():
        merge_yaml_files(dest, sources)
        for src_rel in sources:
            remove_path(src_rel)

    section("6. Rewrite modules: entries with new filenames")
    mod_changes = update_module_paths(MODULE_MAP, REPO_ROOT)
    for f, _ in sorted(mod_changes.items()):
        print(f"  {f}: modules rewritten")

    section("7. Move runtime/ -> src/")
    runtime = REPO_ROOT / "runtime"
    src_dir = REPO_ROOT / "src"
    if runtime.exists():
        for child in runtime.iterdir():
            target = src_dir / child.name
            shutil.move(str(child), str(target))
            print(f"  move: runtime/{child.name} -> src/{child.name}")
        runtime.rmdir()
        print("  rmdir: runtime/")

    section("8. Clean up empty source directories")
    for d in ("stdlib", "templates", "examples"):
        remove_empty_dir(d)

    section("9. Final verification")
    broken = list_broken_relationships(REPO_ROOT)
    if broken:
        print("  ERROR: broken relationships after moves:")
        for r in broken:
            print(f"    {r.source_id} --{r.kind}--> {r.target_id}  ({r.source_file})")
        sys.exit(1)
    print("  OK: zero broken relationships")

    files = discover_yaml_files(REPO_ROOT)
    print(f"  YAML files remaining: {len(files)}")
    for p in sorted(files):
        print(f"    {p.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
