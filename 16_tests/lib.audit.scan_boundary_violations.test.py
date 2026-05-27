"""Tests for lib.audit.scan_boundary_violations.

All tests use tmp_path and synthetic file trees — no network, no subprocess.
"""

from __future__ import annotations

import json
from pathlib import Path

from lib.audit.scan_boundary_violations import (
    VALID_STATUSES,
    _bucket,
    _finding,
    _lines_with,
    audit_file,
    iter_audited_files,
    preserve_statuses,
    run_audit,
)

# ---------------------------------------------------------------------------
# _bucket
# ---------------------------------------------------------------------------


def test_bucket_returns_first_part_for_numbered_dirs(tmp_path: Path) -> None:
    path = tmp_path / "07_lib" / "something.py"
    assert _bucket(path, tmp_path) == "07_lib"


def test_bucket_returns_workspace_root_for_files_at_root(tmp_path: Path) -> None:
    path = tmp_path / "README.md"
    assert _bucket(path, tmp_path) == "workspace_root"


def test_bucket_returns_workspace_root_for_non_numeric_prefix(tmp_path: Path) -> None:
    path = tmp_path / "scripts" / "run.sh"
    assert _bucket(path, tmp_path) == "workspace_root"


# ---------------------------------------------------------------------------
# _lines_with
# ---------------------------------------------------------------------------


def test_lines_with_finds_needle() -> None:
    text = "line1\nimport ollama\nline3"
    result = _lines_with(text, ["import ollama"])
    assert len(result) == 1
    assert result[0]["line"] == 2
    assert "ollama" in result[0]["excerpt"]


def test_lines_with_deduplicates_needles() -> None:
    text = "import ollama\nimport ollama again"
    result = _lines_with(text, ["import ollama"])
    # Same needle only reported once
    assert len(result) == 1


def test_lines_with_respects_limit() -> None:
    text = "\n".join([f"needle {i}" for i in range(10)])
    result = _lines_with(text, [f"needle {i}" for i in range(10)], limit=3)
    assert len(result) <= 3


def test_lines_with_empty_text() -> None:
    result = _lines_with("", ["needle"])
    assert result == []


def test_lines_with_no_match() -> None:
    result = _lines_with("hello world\nfoo bar", ["import requests"])
    assert result == []


# ---------------------------------------------------------------------------
# _finding
# ---------------------------------------------------------------------------


def test_finding_schema_version(tmp_path: Path) -> None:
    f = tmp_path / "test.py"
    f.write_text("import ollama")
    result = _finding(
        f, tmp_path, "2024-01-01T00:00:00", "test_rule", "high", "summary", [], [], []
    )
    assert result["schema_version"] == "1.0"


def test_finding_id_is_deterministic(tmp_path: Path) -> None:
    f = tmp_path / "test.py"
    f.write_text("import ollama")
    r1 = _finding(f, tmp_path, "2024", "rule_x", "high", "s", [], [], [])
    r2 = _finding(f, tmp_path, "2024", "rule_x", "high", "s", [], [], [])
    assert r1["finding_id"] == r2["finding_id"]


def test_finding_status_is_open(tmp_path: Path) -> None:
    f = tmp_path / "test.py"
    f.write_text("")
    result = _finding(f, tmp_path, "2024", "rule", "medium", "summary", [], [], [])
    assert result["status"] == "open"


def test_finding_severity_stored_correctly(tmp_path: Path) -> None:
    f = tmp_path / "test.py"
    f.write_text("")
    result = _finding(f, tmp_path, "2024", "rule", "medium", "summary", [], [], [])
    assert result["violation"]["severity"] == "medium"


# ---------------------------------------------------------------------------
# iter_audited_files
# ---------------------------------------------------------------------------


def test_iter_audited_files_includes_py_files(tmp_path: Path) -> None:
    (tmp_path / "07_lib").mkdir()
    (tmp_path / "07_lib" / "foo.py").write_text("x = 1")
    output_dir = tmp_path / "14_data"
    output_dir.mkdir()
    files = iter_audited_files(tmp_path, output_dir)
    assert any(f.name == "foo.py" for f in files)


def test_iter_audited_files_excludes_output_dir(tmp_path: Path) -> None:
    output_dir = tmp_path / "14_data" / "out"
    output_dir.mkdir(parents=True)
    (output_dir / "findings.jsonl").write_text("")
    files = iter_audited_files(tmp_path, output_dir)
    assert not any("findings.jsonl" in str(f) for f in files)


def test_iter_audited_files_excludes_pycache(tmp_path: Path) -> None:
    cache = tmp_path / "07_lib" / "__pycache__"
    cache.mkdir(parents=True)
    (cache / "module.pyc").write_text("")
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    files = iter_audited_files(tmp_path, output_dir)
    assert not any("__pycache__" in str(f) for f in files)


def test_iter_audited_files_excludes_data_bucket(tmp_path: Path) -> None:
    data = tmp_path / "14_data"
    data.mkdir()
    (data / "results.json").write_text("{}")
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    files = iter_audited_files(tmp_path, output_dir)
    assert not any("14_data" in f.parts for f in files)


def test_iter_audited_files_only_audited_suffixes(tmp_path: Path) -> None:
    (tmp_path / "stuff").mkdir()
    (tmp_path / "stuff" / "file.csv").write_text("a,b")
    (tmp_path / "stuff" / "file.py").write_text("x = 1")
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    files = iter_audited_files(tmp_path, output_dir)
    assert not any(f.suffix == ".csv" for f in files)
    assert any(f.suffix == ".py" for f in files)


# ---------------------------------------------------------------------------
# audit_file — rule detection
# ---------------------------------------------------------------------------


def test_audit_file_detects_provider_execution_in_tool_bucket(tmp_path: Path) -> None:
    lib_dir = tmp_path / "07_lib" / "research"
    lib_dir.mkdir(parents=True)
    victim = lib_dir / "summarize.py"
    victim.write_text("from langchain_community.chat_models import ChatOllama\n")
    findings = audit_file(victim, tmp_path, "2024-01-01")
    codes = [f["violation"]["code"] for f in findings]
    assert "provider_execution_in_tool_bucket" in codes


def test_audit_file_detects_executable_wrapper_in_prompt_bucket(tmp_path: Path) -> None:
    prompt_dir = tmp_path / "12_prompts"
    prompt_dir.mkdir()
    victim = prompt_dir / "extract-visible-text.py"
    victim.write_text("import urllib.request\napi_url = 'http://localhost'\n")
    findings = audit_file(victim, tmp_path, "2024-01-01")
    codes = [f["violation"]["code"] for f in findings]
    assert "executable_provider_wrapper_in_prompt_bucket" in codes


def test_audit_file_returns_empty_for_clean_file(tmp_path: Path) -> None:
    lib_dir = tmp_path / "07_lib" / "clean"
    lib_dir.mkdir(parents=True)
    clean = lib_dir / "utils.py"
    clean.write_text("def add(a, b): return a + b\n")
    findings = audit_file(clean, tmp_path, "2024-01-01")
    assert findings == []


# ---------------------------------------------------------------------------
# preserve_statuses
# ---------------------------------------------------------------------------


def test_preserve_statuses_carries_forward_valid_status(tmp_path: Path) -> None:
    prev_path = tmp_path / "findings.jsonl"
    finding = {
        "finding_id": "CAF-AABBCC001122",
        "status": "accepted",
        "schema_version": "1.0",
        "violation": {"severity": "high"},
    }
    prev_path.write_text(json.dumps(finding) + "\n")
    current = [{"finding_id": "CAF-AABBCC001122", "status": "open"}]
    preserve_statuses(current, prev_path)
    assert current[0]["status"] == "accepted"


def test_preserve_statuses_keeps_open_for_unknown_id(tmp_path: Path) -> None:
    prev_path = tmp_path / "findings.jsonl"
    prev_path.write_text(json.dumps({"finding_id": "CAF-OTHER", "status": "resolved"}) + "\n")
    current = [{"finding_id": "CAF-NEW", "status": "open"}]
    preserve_statuses(current, prev_path)
    assert current[0]["status"] == "open"


def test_preserve_statuses_does_nothing_if_file_missing(tmp_path: Path) -> None:
    current = [{"finding_id": "CAF-X", "status": "open"}]
    preserve_statuses(current, tmp_path / "nonexistent.jsonl")
    assert current[0]["status"] == "open"


# ---------------------------------------------------------------------------
# VALID_STATUSES constant
# ---------------------------------------------------------------------------


def test_valid_statuses_contains_expected_values() -> None:
    assert "open" in VALID_STATUSES
    assert "accepted" in VALID_STATUSES
    assert "resolved" in VALID_STATUSES
    assert "dismissed" in VALID_STATUSES


# ---------------------------------------------------------------------------
# run_audit — integration (no violations expected in a minimal workspace)
# ---------------------------------------------------------------------------


def test_run_audit_returns_summary_with_required_keys(tmp_path: Path) -> None:
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    _findings, summary = run_audit(tmp_path, output_dir)
    assert "schema_version" in summary
    assert "files_scanned" in summary
    assert "findings" in summary
    assert isinstance(_findings, list)


def test_run_audit_sorts_by_severity(tmp_path: Path) -> None:
    """High-severity findings appear before medium in the sorted output."""
    lib_dir = tmp_path / "07_lib" / "x"
    lib_dir.mkdir(parents=True)
    # Create a file that triggers the high-severity provider_execution rule
    (lib_dir / "tool.py").write_text("import ollama\nollama.generate('hi')\n")
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    findings, _ = run_audit(tmp_path, output_dir)
    if len(findings) >= 2:
        severities = [f["violation"]["severity"] for f in findings]
        order = {"high": 0, "medium": 1, "low": 2}
        assert all(
            order[severities[i]] <= order[severities[i + 1]] for i in range(len(severities) - 1)
        )
