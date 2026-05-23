from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[2] / "17_scripts" / "audit_classifications.py"
SPEC = importlib.util.spec_from_file_location("audit_classifications", SCRIPT)
assert SPEC and SPEC.loader
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


def test_prompt_executable_is_flagged(tmp_path: Path) -> None:
    workspace = tmp_path / "20_workspaces"
    prompt = workspace / "12_prompts" / "tasks" / "vision.py"
    prompt.parent.mkdir(parents=True)
    prompt.write_text(
        'import urllib.request\napi_url = "http://localhost"\nprompt = "describe"\n',
        encoding="utf-8",
    )

    findings = AUDIT.audit_file(prompt, workspace, "2026-05-23T00:00:00+00:00")

    assert [finding["violation"]["code"] for finding in findings] == [
        "executable_provider_wrapper_in_prompt_bucket"
    ]
    assert findings[0]["file"] == str(prompt.resolve())


def test_mcp_documentation_is_not_mistaken_for_execution(tmp_path: Path) -> None:
    workspace = tmp_path / "20_workspaces"
    readme = workspace / "11_mcp" / "tools" / "README.md"
    readme.parent.mkdir(parents=True)
    readme.write_text("Document usage: `ollama.generate(...)`.\n", encoding="utf-8")

    findings = AUDIT.audit_file(readme, workspace, "2026-05-23T00:00:00+00:00")

    assert findings == []


def test_tool_provider_execution_includes_harness_destination(tmp_path: Path) -> None:
    workspace = tmp_path / "20_workspaces"
    tool = workspace / "07_tools" / "vision" / "client.py"
    tool.parent.mkdir(parents=True)
    tool.write_text("from langchain_ollama import ChatOllama\n", encoding="utf-8")

    findings = AUDIT.audit_file(tool, workspace, "2026-05-23T00:00:00+00:00")

    assert findings[0]["violation"]["code"] == "provider_execution_in_tool_bucket"
    assert "04_harnesses" in {
        target["class"] for target in findings[0]["decomposition_classes"]
    }


def test_rescan_preserves_review_status(tmp_path: Path) -> None:
    findings = [{"finding_id": "CAF-ABCDEF123456", "status": "open"}]
    previous = tmp_path / "findings.jsonl"
    previous.write_text(
        json.dumps({"finding_id": "CAF-ABCDEF123456", "status": "accepted"}) + "\n",
        encoding="utf-8",
    )

    AUDIT.preserve_statuses(findings, previous)

    assert findings[0]["status"] == "accepted"
