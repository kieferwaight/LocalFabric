#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import sys

from core.paths import REPO_ROOT, data
from tools.classify.media import classify_file
from tools.files import iter_files, sha256_file, write_json
from tools.metadata.extract import infer_source_guess

MANIFESTS_DIR = data("manifests")
CONFIDENCE_REVIEW_THRESHOLD = 0.80


def build_classification(root: Path) -> tuple[dict, dict, dict]:
    items = []
    fingerprint_map: dict[str, list[str]] = {}
    class_counter = Counter()

    for abs_path in iter_files(root):
        rel = abs_path.relative_to(root)
        info = classify_file(rel)
        stat = abs_path.stat()
        file_hash = sha256_file(abs_path)
        fingerprint_map.setdefault(file_hash, []).append(rel.as_posix())

        if info["confidence"] < CONFIDENCE_REVIEW_THRESHOLD and info["class"] != "needs_review":
            info["class"] = "needs_review"
            info["subclass"] = "low_confidence"
            info["recommended_destination"] = "00_todo/pending/"
            info["reason"] = f"Low confidence routing ({info['confidence']:.2f})"

        record = {
            "source_path": rel.as_posix(),
            "filename": rel.name,
            "extension": rel.suffix.lower(),
            "size_bytes": stat.st_size,
            "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
            "hash_sha256": file_hash,
            "source_guess": infer_source_guess(rel),
            "class": info["class"],
            "subclass": info["subclass"],
            "recommended_destination": info["recommended_destination"],
            "confidence": info["confidence"],
            "reason": info["reason"],
        }
        items.append(record)
        class_counter[record["class"]] += 1

    duplicates = []
    for file_hash, paths in fingerprint_map.items():
        if len(paths) > 1:
            duplicates.append({"hash_sha256": file_hash, "paths": sorted(paths), "count": len(paths)})

    items.sort(key=lambda x: x["source_path"])
    duplicates.sort(key=lambda x: (-x["count"], x["paths"][0]))

    classification_report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root": root.as_posix(),
        "review_threshold": CONFIDENCE_REVIEW_THRESHOLD,
        "total_files": len(items),
        "counts_by_class": dict(sorted(class_counter.items(), key=lambda kv: kv[0])),
        "items": items,
    }

    current_state_manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root": root.as_posix(),
        "total_files": len(items),
        "files": [
            {
                "path": item["source_path"],
                "filename": item["filename"],
                "extension": item["extension"],
                "size_bytes": item["size_bytes"],
                "modified_at": item["modified_at"],
                "hash_sha256": item["hash_sha256"],
                "source_guess": item["source_guess"],
            }
            for item in items
        ],
    }

    fingerprint_report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root": root.as_posix(),
        "duplicate_sets": duplicates,
        "total_duplicate_sets": len(duplicates),
    }

    return classification_report, current_state_manifest, fingerprint_report


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
