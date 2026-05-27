"""Tests for lib.classify.build_manifest — build_classification."""

from __future__ import annotations

from pathlib import Path

from lib.classify.build_manifest import CONFIDENCE_REVIEW_THRESHOLD, build_classification

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _make_workspace(tmp_path: Path, files: dict[str, str]) -> Path:
    """Create a minimal workspace tree and return its root."""
    root = tmp_path / "workspace"
    for rel, content in files.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return root


# ---------------------------------------------------------------------------
# return structure
# ---------------------------------------------------------------------------


def test_build_classification_returns_three_dicts(tmp_path: Path) -> None:
    root = _make_workspace(tmp_path, {"misc/doc.md": "# Hello"})
    result = build_classification(root)
    assert isinstance(result, tuple)
    assert len(result) == 3
    classification, manifest, fingerprints = result
    assert isinstance(classification, dict)
    assert isinstance(manifest, dict)
    assert isinstance(fingerprints, dict)


def test_classification_report_has_required_top_level_keys(tmp_path: Path) -> None:
    root = _make_workspace(tmp_path, {"misc/doc.md": "# Hello"})
    classification, _, _ = build_classification(root)
    for key in (
        "generated_at",
        "root",
        "total_files",
        "counts_by_class",
        "items",
        "review_threshold",
    ):
        assert key in classification, f"Missing key: {key}"


def test_manifest_has_required_top_level_keys(tmp_path: Path) -> None:
    root = _make_workspace(tmp_path, {"misc/doc.md": "# Hello"})
    _, manifest, _ = build_classification(root)
    for key in ("generated_at", "root", "total_files", "files"):
        assert key in manifest, f"Missing key: {key}"


def test_fingerprint_report_has_required_top_level_keys(tmp_path: Path) -> None:
    root = _make_workspace(tmp_path, {"misc/doc.md": "# Hello"})
    _, _, fingerprints = build_classification(root)
    for key in ("generated_at", "root", "duplicate_sets", "total_duplicate_sets"):
        assert key in fingerprints, f"Missing key: {key}"


# ---------------------------------------------------------------------------
# happy path — single file
# ---------------------------------------------------------------------------


def test_single_md_file_in_planning_classified_as_content(tmp_path: Path) -> None:
    """Use a high-confidence bucket (90_planning) to avoid the low-confidence reclassification."""
    root = _make_workspace(tmp_path, {"90_planning/roadmap.md": "# Roadmap"})
    classification, manifest, _ = build_classification(root)

    assert classification["total_files"] == 1
    assert manifest["total_files"] == 1
    item = classification["items"][0]
    assert item["class"] == "content"
    assert item["subclass"] == "planning_doc"
    assert item["source_path"] == "90_planning/roadmap.md"
    assert item["filename"] == "roadmap.md"
    assert item["extension"] == ".md"


def test_single_image_classified_as_asset_raw(tmp_path: Path) -> None:
    """Use 10_publication path for images, which routes at 0.88 — above the 0.80 threshold."""
    root = tmp_path / "workspace_img"
    img = (
        root
        / "10_publication_applied_machine_learning"
        / "04_research_and_data"
        / "graphics"
        / "fig.png"
    )
    img.parent.mkdir(parents=True)
    img.write_bytes(b"\x89PNG")
    classification, _, _ = build_classification(root)

    item = classification["items"][0]
    assert item["class"] == "asset_raw"
    assert item["subclass"] == "research_graphic"


def test_single_code_file_in_pipelines_classified_correctly(tmp_path: Path) -> None:
    """Use 07_pipelines/ path which routes at 0.99 — well above the threshold."""
    root = _make_workspace(tmp_path, {"07_pipelines/etl/run.py": "pass"})
    classification, _, _ = build_classification(root)
    item = classification["items"][0]
    assert item["class"] == "pipeline_code"
    assert item["confidence"] >= 0.95


# ---------------------------------------------------------------------------
# multiple files
# ---------------------------------------------------------------------------


def test_multiple_files_all_appear_in_items(tmp_path: Path) -> None:
    root = _make_workspace(
        tmp_path,
        {
            "a/doc.md": "# doc",
            "b/script.py": "pass",
            "c/data.csv": "col1,col2",
        },
    )
    classification, manifest, _ = build_classification(root)
    assert classification["total_files"] == 3
    assert len(classification["items"]) == 3
    assert len(manifest["files"]) == 3


def test_items_are_sorted_by_source_path(tmp_path: Path) -> None:
    root = _make_workspace(
        tmp_path,
        {
            "z/z.md": "z",
            "a/a.md": "a",
            "m/m.md": "m",
        },
    )
    classification, _, _ = build_classification(root)
    paths = [item["source_path"] for item in classification["items"]]
    assert paths == sorted(paths)


# ---------------------------------------------------------------------------
# counts_by_class
# ---------------------------------------------------------------------------


def test_counts_by_class_sums_to_total_files(tmp_path: Path) -> None:
    root = _make_workspace(
        tmp_path,
        {
            "docs/a.md": "# a",
            "docs/b.md": "# b",
            "code/c.py": "pass",
        },
    )
    classification, _, _ = build_classification(root)
    assert sum(classification["counts_by_class"].values()) == classification["total_files"]


# ---------------------------------------------------------------------------
# low-confidence reclassification
# ---------------------------------------------------------------------------


def test_low_confidence_file_reclassified_to_needs_review(tmp_path: Path) -> None:
    """Files with confidence below the threshold and a non-needs_review class are reclassified.

    A generic .md file under notes/ routes as 'content' with confidence 0.76, which is
    below the CONFIDENCE_REVIEW_THRESHOLD of 0.80 — the manifest reclassifies it.
    """
    root = _make_workspace(tmp_path, {"notes/overview.md": "Hello"})
    classification, _, _ = build_classification(root)

    item = classification["items"][0]
    # Originally classified as 'content' but below threshold — reclassified
    assert item["class"] == "needs_review"
    assert item["subclass"] == "low_confidence"
    assert item["recommended_destination"] == "00_todo/pending/"
    assert "Low confidence" in item["reason"]


def test_already_needs_review_not_double_reclassified(tmp_path: Path) -> None:
    """Files that already classify as needs_review are not double-reclassified.

    An unknown extension (.xyz) routes directly to needs_review/unknown with confidence 0.40.
    The reclassification guard (info['class'] != 'needs_review') prevents overwriting subclass.
    """
    root = _make_workspace(tmp_path, {"inbox/file.xyz": "???"})
    classification, _, _ = build_classification(root)

    item = classification["items"][0]
    # Keeps the original subclass from classify_file, not the reclassification subclass
    assert item["class"] == "needs_review"
    assert item["subclass"] == "unknown"  # original, not "low_confidence"


def test_high_confidence_file_not_reclassified(tmp_path: Path) -> None:
    """Files with confidence >= threshold keep their original class.

    Uses 90_planning/ which yields confidence 0.97 — well above 0.80.
    (20_backups/ is excluded by iter_files and would produce an empty items list.)
    """
    root = _make_workspace(tmp_path, {"90_planning/plan.md": "# Plan"})
    classification, _, _ = build_classification(root)

    item = classification["items"][0]
    assert item["class"] == "content"
    assert item["subclass"] == "planning_doc"
    assert item["confidence"] >= CONFIDENCE_REVIEW_THRESHOLD


# ---------------------------------------------------------------------------
# duplicate detection
# ---------------------------------------------------------------------------


def test_identical_files_detected_as_duplicates(tmp_path: Path) -> None:
    content = "identical content for dedup test"
    root = _make_workspace(
        tmp_path,
        {
            "area_a/copy1.md": content,
            "area_b/copy2.md": content,
        },
    )
    _, _, fingerprints = build_classification(root)

    assert fingerprints["total_duplicate_sets"] == 1
    dup = fingerprints["duplicate_sets"][0]
    assert dup["count"] == 2
    paths = dup["paths"]
    assert "area_a/copy1.md" in paths
    assert "area_b/copy2.md" in paths


def test_unique_files_produce_no_duplicates(tmp_path: Path) -> None:
    root = _make_workspace(
        tmp_path,
        {
            "a/unique1.md": "content one",
            "b/unique2.md": "content two",
        },
    )
    _, _, fingerprints = build_classification(root)
    assert fingerprints["total_duplicate_sets"] == 0
    assert fingerprints["duplicate_sets"] == []


# ---------------------------------------------------------------------------
# hash correctness
# ---------------------------------------------------------------------------


def test_sha256_hash_present_in_item(tmp_path: Path) -> None:
    root = _make_workspace(tmp_path, {"data/file.txt": "hello"})
    classification, _, _ = build_classification(root)

    item = classification["items"][0]
    assert "hash_sha256" in item
    assert len(item["hash_sha256"]) == 64  # sha256 hex digest


def test_sha256_in_manifest_matches_classification(tmp_path: Path) -> None:
    root = _make_workspace(tmp_path, {"data/file.txt": "hello"})
    classification, manifest, _ = build_classification(root)

    cls_hash = classification["items"][0]["hash_sha256"]
    mft_hash = manifest["files"][0]["hash_sha256"]
    assert cls_hash == mft_hash


# ---------------------------------------------------------------------------
# determinism (stability — audit relies on stable hashes)
# ---------------------------------------------------------------------------


def test_build_classification_is_deterministic(tmp_path: Path) -> None:
    """Same workspace tree must produce identical items (excluding generated_at timestamps)."""
    root = _make_workspace(
        tmp_path,
        {
            "docs/readme.md": "# Readme",
            "scripts/build.py": "pass",
            "data/metrics.csv": "x,y\n1,2",
        },
    )
    first, _, _ = build_classification(root)
    second, _, _ = build_classification(root)

    # Strip timestamp fields before comparison
    def _strip_ts(items: list[dict]) -> list[dict]:
        return [{k: v for k, v in item.items() if k != "modified_at"} for item in items]

    assert _strip_ts(first["items"]) == _strip_ts(second["items"])


def test_hash_stable_for_unchanged_file(tmp_path: Path) -> None:
    root = _make_workspace(tmp_path, {"notes/stable.md": "unchanged content"})
    first, _, _ = build_classification(root)
    second, _, _ = build_classification(root)

    assert first["items"][0]["hash_sha256"] == second["items"][0]["hash_sha256"]


# ---------------------------------------------------------------------------
# empty workspace
# ---------------------------------------------------------------------------


def test_empty_workspace_returns_zero_totals(tmp_path: Path) -> None:
    root = tmp_path / "empty_workspace"
    root.mkdir()
    classification, manifest, fingerprints = build_classification(root)

    assert classification["total_files"] == 0
    assert classification["items"] == []
    assert manifest["total_files"] == 0
    assert manifest["files"] == []
    assert fingerprints["total_duplicate_sets"] == 0
