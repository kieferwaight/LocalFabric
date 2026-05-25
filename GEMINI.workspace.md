# Workspaces Gemini Instructions

This document provides scoped instructions for working within the implementation buckets in `20_workspaces/`.

## Import Strategy

Numeric prefixes (e.g., `01_`, `02_`) are for filesystem organization only. **Never use the numeric prefix in Python imports.**

*   **Clean Names:** Use the aliases defined in `pyproject.toml`.
    *   `from core.paths import ...` (maps to `02_core/src/core/`)
    *   `from adapters.cli import ...` (maps to `03_adapters/cli/`)
    *   `from harnesses.base import ...` (maps to `04_harnesses/base.py`)
*   **Resolution:** If imports don't resolve, ensure you have run `pip install -e .` from the `20_workspaces/` directory.

## Path Resolution

*   **Canonical Anchor:** Always use `core.paths.WORKSPACES_ROOT` for path resolution.
*   **Avoid Relatives:** Do not use `os.path.join(__file__, "..")` or similar patterns to escape the current directory.
*   **Data Paths:** Reference persistent state under `14_data/` using path-based addressing.

## Service Runtime

Services are executed using the `service_runtime` bucket:
*   `python -m service_runtime.cmd up <service> <data-path>`
*   Available services are in `09_services/`.
*   Data paths should be under `14_data/stores/` or `14_data/apps/`.

## Classification Audit

Before proposing any changes, run the classification audit to ensure no cross-layer responsibility leaks:

```bash
# From 20_workspaces/
python -m scripts.audit_classifications
```

Audit results are stored in `14_data/runs/classification_audit/`. Resolving these findings is mandatory for merging.
