#!/usr/bin/env python3
"""CLI shim: classify files and write baseline manifests.

The classification logic lives in tasks.classify.build_manifest.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from core.environment import REPO_ROOT, data
from tasks.classify.build_manifest import build_classification
from tasks.files import write_json

MANIFESTS_DIR = data("manifests")


def main() -> None:
    parser = argparse.ArgumentParser(description="Classify files and generate baseline manifests")
    parser.add_argument("--root", default=str(REPO_ROOT), help="Repository root")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)

    classification_report, current_state_manifest, fingerprint_report = build_classification(root)

    write_json(MANIFESTS_DIR / "classification_report.json", classification_report)
    write_json(MANIFESTS_DIR / "current_state_manifest.json", current_state_manifest)
    write_json(MANIFESTS_DIR / "fingerprint_report.json", fingerprint_report)

    print("Wrote classification_report.json")
    print("Wrote current_state_manifest.json")
    print("Wrote fingerprint_report.json")


if __name__ == "__main__":
    main()
