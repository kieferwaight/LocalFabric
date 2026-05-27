"""Tests for lib.classify.media — classify_file and media_class_for_path."""

from __future__ import annotations

from pathlib import Path

import pytest

from lib.classify.media import classify_file, media_class_for_path


# ---------------------------------------------------------------------------
# media_class_for_path — broad ingest triage
# ---------------------------------------------------------------------------


def test_media_class_for_path_image_extensions() -> None:
    for ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".tiff", ".tif", ".bmp"):
        assert media_class_for_path(Path(f"some/file{ext}")) == "image", ext


def test_media_class_for_path_document_extensions() -> None:
    for ext in (".pdf", ".docx", ".doc", ".txt", ".md"):
        assert media_class_for_path(Path(f"some/file{ext}")) == "document", ext


def test_media_class_for_path_unknown_extension() -> None:
    assert media_class_for_path(Path("archive.zip")) == "unknown"
    assert media_class_for_path(Path("data.csv")) == "unknown"
    assert media_class_for_path(Path("script.py")) == "unknown"


def test_media_class_for_path_case_insensitive() -> None:
    assert media_class_for_path(Path("PHOTO.PNG")) == "image"
    assert media_class_for_path(Path("REPORT.PDF")) == "document"


def test_media_class_for_path_no_extension() -> None:
    assert media_class_for_path(Path("Makefile")) == "unknown"


# ---------------------------------------------------------------------------
# classify_file — routing recommendations
# ---------------------------------------------------------------------------

# --- result structure ---


def test_classify_file_returns_required_keys() -> None:
    result = classify_file(Path("some/file.md"))
    assert set(result.keys()) == {"class", "subclass", "recommended_destination", "confidence", "reason"}


# --- backup bucket ---


def test_classify_file_backup_bucket() -> None:
    result = classify_file(Path("20_backups/something.py"))
    assert result["class"] == "backup"
    assert result["confidence"] >= 0.95


# --- pipeline bucket ---


def test_classify_file_pipeline_bucket() -> None:
    result = classify_file(Path("07_pipelines/etl/run.py"))
    assert result["class"] == "pipeline_code"
    assert result["confidence"] >= 0.95


# --- code extension happy path ---


def test_classify_file_code_extension_defaults_to_pipeline_code() -> None:
    result = classify_file(Path("some_random_folder/helper.py"))
    assert result["class"] == "pipeline_code"
    assert result["subclass"] == "code_generic"
    assert result["recommended_destination"].startswith("07_pipelines/")


def test_classify_file_javascript_is_code() -> None:
    result = classify_file(Path("stuff/app.js"))
    assert result["class"] == "pipeline_code"


# --- document extension happy paths ---


def test_classify_file_doc_defaults_to_content_draft() -> None:
    result = classify_file(Path("misc/overview.md"))
    assert result["class"] == "content"
    assert result["subclass"] == "draft_doc"


def test_classify_file_evidence_doc_routed_to_trust_database() -> None:
    result = classify_file(Path("misc/claim_evidence.md"))
    assert result["class"] == "trust_evidence"
    assert "04_trust_database" in result["recommended_destination"]


def test_classify_file_planning_doc_stays_in_planning() -> None:
    result = classify_file(Path("90_planning/q3_roadmap.md"))
    assert result["class"] == "content"
    assert result["subclass"] == "planning_doc"
    assert result["recommended_destination"].startswith("90_planning/")


def test_classify_file_knowledgebase_doc_stays_in_knowledgebase() -> None:
    result = classify_file(Path("90_knowledgebase/concepts/embeddings.md"))
    assert result["class"] == "content"
    assert result["subclass"] == "knowledgebase_doc"
    assert result["recommended_destination"].startswith("90_knowledgebase/")


# --- image extension happy path ---


def test_classify_file_image_defaults_to_asset_raw() -> None:
    result = classify_file(Path("photos/snapshot.png"))
    assert result["class"] == "asset_raw"
    assert result["subclass"] == "image"


# --- data extension happy path ---


def test_classify_file_data_extension_routed_to_ml_dataset() -> None:
    result = classify_file(Path("exports/results.csv"))
    assert result["class"] == "ml_dataset"
    assert result["subclass"] == "data_file"


def test_classify_file_yaml_is_data() -> None:
    result = classify_file(Path("configs/settings.yaml"))
    assert result["class"] == "ml_dataset"


# --- archive extension ---


def test_classify_file_archive_routed_to_archive_bucket() -> None:
    result = classify_file(Path("downloads/package.zip"))
    assert result["class"] == "archive"
    assert result["subclass"] == "archive_file"


# --- unknown / needs_review ---


def test_classify_file_unknown_extension_needs_review() -> None:
    result = classify_file(Path("oddball/file.xyz"))
    assert result["class"] == "needs_review"
    assert result["subclass"] == "unknown"
    assert result["recommended_destination"].startswith("00_todo/")


# --- publication ML research bucket ---


def test_classify_file_external_sources_ml_research() -> None:
    result = classify_file(
        Path("10_publication_applied_machine_learning/02_external_sources/paper.pdf")
    )
    assert result["class"] == "ml_research"
    assert result["subclass"] == "external_source"


def test_classify_file_research_data_is_ml_dataset() -> None:
    result = classify_file(
        Path("10_publication_applied_machine_learning/04_research_and_data/data/results.csv")
    )
    assert result["class"] == "ml_dataset"
    assert result["subclass"] == "research_data"


def test_classify_file_research_code_becomes_pipeline_script() -> None:
    result = classify_file(
        Path("10_publication_applied_machine_learning/04_research_and_data/code/train.py")
    )
    assert result["class"] == "pipeline_code"
    assert result["subclass"] == "research_utility"


def test_classify_file_research_graphic_treated_as_asset() -> None:
    result = classify_file(
        Path(
            "10_publication_applied_machine_learning/04_research_and_data/graphics/figure1.png"
        )
    )
    assert result["class"] == "asset_raw"
    assert result["subclass"] == "research_graphic"


def test_classify_file_distribution_outputs_are_exports() -> None:
    result = classify_file(
        Path("10_publication_applied_machine_learning/09_distribution/packet.zip")
    )
    assert result["class"] == "export"
    assert result["confidence"] >= 0.95


def test_classify_file_internal_knowledge_doc_is_content() -> None:
    result = classify_file(
        Path(
            "10_publication_applied_machine_learning/02_internal_knowledge/overview.md"
        )
    )
    assert result["class"] == "content"
    assert result["subclass"] == "internal_draft"


def test_classify_file_internal_knowledge_image_is_diagram_asset() -> None:
    result = classify_file(
        Path(
            "10_publication_applied_machine_learning/02_internal_knowledge/arch.png"
        )
    )
    assert result["class"] == "asset_processed"
    assert result["subclass"] == "internal_visual"


# --- edge cases: paths outside any known bucket ---


def test_classify_file_deep_unknown_path_does_not_raise() -> None:
    result = classify_file(Path("a/b/c/d/e/f/g.unknown"))
    assert isinstance(result["class"], str)


def test_classify_file_root_level_file() -> None:
    result = classify_file(Path("README.md"))
    assert result["class"] == "content"


def test_classify_file_path_with_no_extension() -> None:
    result = classify_file(Path("some/Makefile"))
    assert result["class"] == "needs_review"


# --- determinism (stability) ---


def test_classify_file_same_input_same_output() -> None:
    paths = [
        "misc/doc.md",
        "photos/img.jpg",
        "scripts/run.py",
        "data/results.csv",
        "downloads/bundle.zip",
        "oddball/thing.xyz",
        "90_planning/roadmap.txt",
        "20_backups/old.py",
    ]
    for raw in paths:
        p = Path(raw)
        first = classify_file(p)
        second = classify_file(p)
        assert first == second, f"Non-deterministic output for {raw!r}"


def test_classify_file_confidence_in_valid_range() -> None:
    """All confidence scores must be in [0.0, 1.0]."""
    paths = [
        "misc/doc.md",
        "photos/img.jpg",
        "scripts/run.py",
        "data/results.csv",
        "downloads/bundle.zip",
        "oddball/thing.xyz",
        "20_backups/old.py",
        "07_pipelines/step.py",
        "10_publication_applied_machine_learning/09_distribution/packet.zip",
    ]
    for raw in paths:
        result = classify_file(Path(raw))
        assert 0.0 <= result["confidence"] <= 1.0, f"Out-of-range confidence for {raw!r}"


# --- excluded / workspace manifest buckets (14_data / 19_archive analogy) ---


def test_classify_file_backup_path_excluded_from_routing() -> None:
    """20_backups/ is explicitly excluded; classify_file still returns a stable record."""
    result = classify_file(Path("20_backups/archive/dump.json"))
    assert result["class"] == "backup"
    assert "routing" in result["reason"].lower()
