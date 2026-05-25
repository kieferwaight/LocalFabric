from __future__ import annotations

from pathlib import Path

DOC_EXT = {".md", ".txt", ".pdf", ".doc", ".docx", ".gdoc", ".gsheet", ".gslides", ".rtf", ".tex"}
CODE_EXT = {".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".css", ".sh", ".zsh"}
DATA_EXT = {".json", ".jsonl", ".csv", ".tsv", ".yaml", ".yml", ".xml", ".xlsx", ".xls"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}
ARCHIVE_EXT = {".zip", ".tar", ".gz", ".bz2", ".7z"}


def classify_file(rel_path: Path) -> dict:
    rel_norm = rel_path.as_posix().lower()
    ext = rel_path.suffix.lower()

    if rel_norm.startswith("20_backups/") or rel_norm.startswith("20_backups"):
        # Backups are fully excluded from routing — this path should never be reached
        return _result("backup", "cold_backup", "20_backups/", 0.99, "Inside backup area — excluded from routing")

    if rel_norm.startswith("07_pipelines/"):
        return _result("pipeline_code", "pipeline_internal", "07_pipelines/", 0.99, "Inside pipelines area")

    if rel_norm.startswith("10_publication_applied_machine_learning/02_external_sources/"):
        return _result("ml_research", "external_source", "06_ml/research/", 0.94, "External sources mapped to ML research")

    if rel_norm.startswith("10_publication_applied_machine_learning/04_research_and_data/"):
        if "/code/" in rel_norm:
            return _result("pipeline_code", "research_utility", "07_pipelines/scripts/", 0.90, "Research utilities become pipeline scripts")
        if "/graphics/" in rel_norm or ext in IMAGE_EXT:
            return _result("asset_raw", "research_graphic", "08_assets/raw/imported/", 0.88, "Research graphics treated as assets")
        if ext in DATA_EXT:
            return _result("ml_dataset", "research_data", "06_ml/datasets/raw/", 0.91, "Research and data mapped to datasets")
        return _result("ml_experiment", "research_material", "06_ml/experiments/", 0.84, "Research package content")

    if rel_norm.startswith("10_publication_applied_machine_learning/02_internal_knowledge/"):
        if ext in DOC_EXT:
            return _result("content", "internal_draft", "03_content/drafts/", 0.83, "Internal knowledge docs map to content drafts")
        if ext in IMAGE_EXT:
            return _result("asset_processed", "internal_visual", "08_assets/diagrams/", 0.82, "Internal visuals map to diagram assets")

    if rel_norm.startswith("10_publication_applied_machine_learning/09_distribution/"):
        return _result("export", "publication_distribution", "09_exports/research_packets/", 0.96, "Distribution outputs map to exports")

    if ext in CODE_EXT:
        return _result("pipeline_code", "code_generic", "07_pipelines/scripts/", 0.78, "Code defaults to pipeline scripts")

    if ext in DOC_EXT:
        if "claim" in rel_norm or "evidence" in rel_norm:
            return _result("trust_evidence", "evidence_doc", "04_trust_database/evidence/", 0.84, "Evidence-like document")
        if rel_norm.startswith("90_planning/"):
            return _result("content", "planning_doc", "90_planning/", 0.97, "Planning documents stay in planning")
        if rel_norm.startswith("90_knowledgebase/"):
            return _result("content", "knowledgebase_doc", "90_knowledgebase/", 0.97, "Knowledgebase remains curated")
        return _result("content", "draft_doc", "03_content/drafts/", 0.76, "Documentation defaults to content drafts")

    if ext in IMAGE_EXT:
        return _result("asset_raw", "image", "08_assets/raw/imported/", 0.79, "Image defaults to asset ingestion")

    if ext in DATA_EXT:
        return _result("ml_dataset", "data_file", "06_ml/datasets/raw/", 0.79, "Data defaults to ML datasets")

    if ext in ARCHIVE_EXT:
        return _result("archive", "archive_file", "99_archive/unknown/", 0.74, "Archive defaults to unknown archive")

    return _result("needs_review", "unknown", "00_todo/pending/", 0.40, "Unknown type requires manual review")


def _result(top_class: str, subclass: str, destination: str, confidence: float, reason: str) -> dict:
    return {
        "class": top_class,
        "subclass": subclass,
        "recommended_destination": destination,
        "confidence": confidence,
        "reason": reason,
    }
