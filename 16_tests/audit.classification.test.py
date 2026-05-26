from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "17_scripts" / "audit_classifications.py"
SPEC = importlib.util.spec_from_file_location("audit_classifications", SCRIPT)
assert SPEC and SPEC.loader
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


def test_prompt_executable_is_flagged(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    prompt = workspace / "12_prompts" / "tasks.vision.py"
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
    workspace = tmp_path / "workspace"
    readme = workspace / "11_mcp" / "tools" / "README.md"
    readme.parent.mkdir(parents=True)
    readme.write_text("Document usage: `ollama.generate(...)`.\n", encoding="utf-8")

    findings = AUDIT.audit_file(readme, workspace, "2026-05-23T00:00:00+00:00")

    assert findings == []


def test_tool_provider_execution_includes_harness_destination(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    tool = workspace / "07_tasks" / "vision" / "client.py"
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


def test_workflow_open_write_is_flagged_for_driver_extraction(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workflow = workspace / "06_workflows" / "job.py"
    workflow.parent.mkdir(parents=True)
    workflow.write_text(
        'with open("report.md", "w") as handle:\n    handle.write("report")\n',
        encoding="utf-8",
    )

    findings = AUDIT.audit_file(workflow, workspace, "2026-05-23T00:00:00+00:00")

    assert findings[0]["violation"]["code"] == "workflow_owns_persistent_file_io"


def test_generated_workflow_documentation_is_not_scanned_as_executable_io(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    documentation = workspace / "06_workflows" / "yaml" / "docs" / "definition.md"
    documentation.parent.mkdir(parents=True)
    documentation.write_text("Example: `target.write_text(content)`.\n", encoding="utf-8")

    findings = AUDIT.audit_file(documentation, workspace, "2026-05-23T00:00:00+00:00")

    assert findings == []
