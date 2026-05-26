"""Thin shim that drives doc generation through the YAML workflow engine.

Both the repo README and the per-definition YAML API reference are now
defined as YAML workflow definitions under `06_workflows/yaml/definitions/`.
This script just forwards to the interpreter so existing entry points
(`make docs`, `uv run 17_scripts/generate_docs.py`) keep working.

  - README.md is rendered from `docs.readme` (see `docs.readme.yaml`),
    reading `pyproject.toml` for the dynamic sections.
  - The YAML API reference (index, schema, per-definition pages) lands
    flat in `18_docs/` with the `workflows.yaml.` prefix, driven by
    `docs.api.reference` (see `docs.yaml`).
  - The classification audit + remediation workflow docs are emitted from
    static template definitions in `docs.classification.yaml` so manual
    edits can't silently overwrite the canonical text.

Pass `--check` to verify committed output instead of regenerating it.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
INTERPRETER = REPO_ROOT / "06_workflows" / "yaml" / "interpreter.py"
README_YAML = REPO_ROOT / "06_workflows" / "yaml" / "definitions" / "docs.readme.yaml"
API_REF_YAML = REPO_ROOT / "06_workflows" / "yaml" / "definitions" / "docs.yaml"
CLASSIFICATION_YAML = (
    REPO_ROOT / "06_workflows" / "yaml" / "definitions" / "docs.classification.yaml"
)


def _run(yaml_file: Path, def_id: str, mode: str, extra: list[str]) -> int:
    cmd = [
        sys.executable, str(INTERPRETER), str(yaml_file), def_id, f"--mode={mode}",
        *extra,
    ]
    print(f"$ {' '.join(cmd)}", flush=True)
    return subprocess.call(cmd, cwd=REPO_ROOT)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    mode = "check" if "--check" in argv else "write"

    readme_rc = _run(README_YAML, "docs.readme", mode, [])
    if readme_rc != 0:
        return readme_rc
    classification_rc = _run(
        CLASSIFICATION_YAML, "docs.classification", mode, ["--output_dir=18_docs"]
    )
    if classification_rc != 0:
        return classification_rc
    api_rc = _run(API_REF_YAML, "docs.api.reference", mode, ["--output_dir=18_docs"])
    return api_rc


if __name__ == "__main__":
    sys.exit(main())
