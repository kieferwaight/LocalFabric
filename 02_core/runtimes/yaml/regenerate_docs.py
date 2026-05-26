#!/usr/bin/env python3
"""Regenerate the comprehensive docs surface into 19_docs/.

Walks every YAML and markdown definition across the listed repo buckets,
populates a single Runtime catalog, and renders one Markdown page per
definition id using the docs.definition.template.definition template.
"""
from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "02_core"))
sys.path.insert(0, str(REPO_ROOT / "02_core" / "runtimes" / "yaml"))

from core.runtimes.markdown import MarkdownHarness
from core.runtimes.yaml.src import Runtime


def _bucket_dir_for(source_path: str) -> str:
    """Map a definition's source_path to its 19_docs/ bucket subdir.

    Most YAML defs have a repo-relative source_path like
    ``09_docker/ollama.yaml``; the first path component is the bucket
    (``09_docker``). Markdown prompts compiled through MarkdownHarness use
    ``<raw>`` (no file path); they all live in ``12_prompts/``.
    """
    if source_path == "<raw>":
        return "12_prompts"
    return source_path.split("/", 1)[0]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Regenerate 19_docs/ from every repo definition")
    parser.add_argument("--output-dir", default="19_docs")
    parser.add_argument("--mode", choices=["write", "check"], default="write")
    args = parser.parse_args(argv)

    output_dir = REPO_ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    runtime = Runtime(
        workflow_dir=str(REPO_ROOT / "02_core" / "runtimes" / "yaml"),
        # Pages live under 19_docs/<source-bucket>/<id>.definition.md; the
        # format here is only used by _update_catalog for cross-link
        # computation. Use the full bucketed shape so parent/mixin/child
        # links resolve correctly.
        definition_page_format="{flat_id}.definition.md",
        index_page="index.md",
        schema_page="schema.md",
    )

    # Bootstrap: load stdlib + all definition modules so base definitions are
    # available before any bucket file references them.
    defs_dir = REPO_ROOT / "02_core" / "runtimes" / "yaml" / "definitions"
    runtime.import_yaml(str(defs_dir / "stdlib.yaml"))
    runtime.execute("stdlib.load-modules", {})
    # schemas.yaml is not a module of stdlib.load-modules; load explicitly.
    runtime.import_yaml(str(defs_dir / "schemas.yaml"))

    markdown_harness = MarkdownHarness(runtime=runtime)

    with warnings.catch_warnings(record=True) as caught_warnings:
        warnings.simplefilter("always")
        counts = runtime.import_repo_wide(REPO_ROOT, markdown_harness=markdown_harness)

    total = sum(counts.values())
    print(f"Loaded {total} definitions across {len(counts)} buckets:")
    for bucket, n in sorted(counts.items()):
        print(f"  {n:4d}  {bucket}")

    if caught_warnings:
        print(f"\nWarnings during import ({len(caught_warnings)}):")
        for w in caught_warnings:
            print(f"  {w.message}")

    # Render one page per definition into the source-bucket subdir so the
    # docs layout mirrors the on-disk YAML/markdown layout.
    rendered = 0
    stale: list[str] = []
    for entry in runtime.globals["catalog"]["definitions"]:
        def_id = entry["id"]
        bucket_dir = _bucket_dir_for(entry["source_path"])
        target_dir = output_dir / bucket_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"{def_id}.definition.md"
        try:
            body = runtime.render_definition(
                "docs.definition.template.definition", {"definition": entry}
            )
        except Exception as exc:
            print(f"  RENDER ERROR: {def_id}: {exc}", file=sys.stderr)
            continue

        rel_name = target.relative_to(output_dir).as_posix()
        if args.mode == "check":
            if not target.exists() or target.read_text() != body:
                print(f"STALE: {rel_name}", file=sys.stderr)
                stale.append(rel_name)
        else:
            target.write_text(body, encoding="utf-8")
            rendered += 1

    # Also render the catalog-wide index + schema pages.
    for tmpl_id, target_name in [
        ("docs.catalog.template.index", "index.md"),
        ("docs.catalog.template.schema", "schema.md"),
    ]:
        try:
            body = runtime.render_definition(tmpl_id, {})
        except Exception as exc:
            print(f"  RENDER ERROR: {tmpl_id}: {exc}", file=sys.stderr)
            continue
        target = output_dir / target_name
        if args.mode == "check":
            if not target.exists() or target.read_text() != body:
                print(f"STALE: {target_name}", file=sys.stderr)
                stale.append(target_name)
        else:
            target.write_text(body, encoding="utf-8")
            rendered += 1

    if args.mode == "check":
        if stale:
            print(f"\n{len(stale)} stale pages detected.", file=sys.stderr)
            return 1
        print(f"\nAll {len(runtime.globals['catalog']['definitions']) + 2} pages are up to date.")
        return 0

    print(f"\nRendered {rendered} pages to {output_dir.relative_to(REPO_ROOT)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
