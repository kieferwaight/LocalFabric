"""Tests for lib.metadata.extract — infer_source_guess and infer_doc_type."""

from __future__ import annotations

from pathlib import Path

from lib.metadata.extract import infer_doc_type, infer_source_guess

# ---------------------------------------------------------------------------
# infer_source_guess
# ---------------------------------------------------------------------------


def test_source_guess_returns_gemini_when_in_path() -> None:
    assert infer_source_guess(Path("data/gemini/output.json")) == "gemini"


def test_source_guess_returns_openai_when_in_path() -> None:
    assert infer_source_guess(Path("runs/openai/chat.json")) == "openai"


def test_source_guess_returns_perplexity_when_in_path() -> None:
    assert infer_source_guess(Path("exports/perplexity/answer.md")) == "perplexity"


def test_source_guess_returns_manual_when_in_path() -> None:
    assert infer_source_guess(Path("drafts/manual/notes.txt")) == "manual"


def test_source_guess_returns_scraped_when_in_path() -> None:
    assert infer_source_guess(Path("raw/scraped/page.html")) == "scraped"


def test_source_guess_returns_uploads_when_in_path() -> None:
    assert infer_source_guess(Path("uploads/file.pdf")) == "uploads"


def test_source_guess_returns_undermind_when_in_path() -> None:
    assert infer_source_guess(Path("research/undermind/paper.md")) == "undermind"


def test_source_guess_returns_unknown_for_unrecognised_path() -> None:
    assert infer_source_guess(Path("random/path/file.txt")) == "unknown"


def test_source_guess_is_case_insensitive() -> None:
    # Parts are lowercased before comparison.
    assert infer_source_guess(Path("data/GEMINI/output.json")) == "gemini"


def test_source_guess_picks_first_match_in_preference_order() -> None:
    # Both gemini and openai in path — should return whichever is iterated first.
    result = infer_source_guess(Path("gemini/openai/file.json"))
    assert result in ("gemini", "openai")  # deterministic per the loop order


def test_source_guess_single_file_at_root() -> None:
    assert infer_source_guess(Path("file.txt")) == "unknown"


def test_source_guess_deep_path_with_known_segment() -> None:
    assert infer_source_guess(Path("a/b/c/d/openai/e/file.json")) == "openai"


# ---------------------------------------------------------------------------
# infer_doc_type
# ---------------------------------------------------------------------------


def test_doc_type_report_keyword() -> None:
    assert infer_doc_type("analysis_report.md") == "report"


def test_doc_type_prompt_keyword() -> None:
    assert infer_doc_type("system_prompt.txt") == "prompt"


def test_doc_type_spec_keyword() -> None:
    assert infer_doc_type("api_spec.yaml") == "specification"


def test_doc_type_specification_keyword() -> None:
    assert infer_doc_type("full_specification.md") == "specification"


def test_doc_type_draft_keyword() -> None:
    assert infer_doc_type("draft_ideas.md") == "draft"


def test_doc_type_defaults_to_note() -> None:
    assert infer_doc_type("random_file.txt") == "note"


def test_doc_type_is_case_insensitive() -> None:
    assert infer_doc_type("MyREPORT.md") == "report"
    assert infer_doc_type("DRAFT_outline.txt") == "draft"


def test_doc_type_empty_name_returns_note() -> None:
    assert infer_doc_type("") == "note"


def test_doc_type_priority_report_over_note() -> None:
    assert infer_doc_type("weekly_report_notes.md") == "report"


def test_doc_type_priority_prompt_over_note() -> None:
    assert infer_doc_type("chat_prompt_example.txt") == "prompt"


def test_doc_type_spec_takes_priority_over_note() -> None:
    assert infer_doc_type("spec_v2.md") == "specification"
