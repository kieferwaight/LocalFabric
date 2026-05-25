# LocalFabric Gemini Instructions

Welcome to the LocalFabric development environment. This document provides foundational guidance for AI agents working in this repository.

## Core Philosophy

LocalFabric is a **local-first, hybrid-ready** AI orchestration platform. Our goal is to provide a unified, provider-agnostic layer over models, tools, and services while maintaining portability and reproducibility.

## Architectural Mandates

1.  **Responsibility-Driven Classification:** All code must live in the correct numeric bucket at the repo root as defined in `REPO_STRUCTURE.md`.
2.  **Strict Layer Separation:**
    *   **Adapters** translate interfaces to internal schemas (stateless).
    *   **Harnesses** manage execution lifecycle (retries, streaming, logging).
    *   **Drivers** provide storage access (normalize backend differences).
    *   **Workflows** orchestrate multi-step logic using harnesses and tools.
3.  **Local-First Execution:** Prefer local models (Ollama, LM Studio) and storage (SQLite, DuckDB) unless remote providers are explicitly required.
4.  **Deterministic Data Model:** All persistent state must live under `14_data/` and be path-addressable.

## Import Strategy

Numeric prefixes (`01_`, `02_`, …) are filesystem-only. **Never use the numeric prefix in Python imports.**

*   **Clean names:** Use the aliases defined in `pyproject.toml`.
    *   `from core.paths import ...` (maps to `02_core/src/core/`)
    *   `from adapters.cli import ...` (maps to `03_adapters/cli/`)
    *   `from harnesses.base import ...` (maps to `04_harnesses/base.py`)
*   **Resolution:** If imports don't resolve, run `pip install -e .` from the repo root.

## Path Resolution

*   **Canonical anchor:** Always use `core.paths.REPO_ROOT` for path resolution.
*   **Avoid relatives:** Do not use `os.path.join(__file__, "..")` or similar patterns to escape the current directory.
*   **Data paths:** Reference persistent state under `14_data/` using path-based addressing.

## Service Runtime

Services are executed using the `service_runtime` bucket:
*   `python -m service_runtime.cmd up <service> <data-path>`
*   Available services are in `09_services/`.
*   Data paths should be under `14_data/stores/` or `14_data/apps/`.

## Development Workflow

1.  **Research:** Use `grep_search` and `glob` to map the codebase. Understand the classification bucket you are working in.
2.  **Strategy:** Draft a plan that respects the layered architecture.
3.  **Execution:** Apply surgical changes. Always use clean import names (e.g., `from core.paths import ...`).
4.  **Validation:**
    *   Run tests relevant to your changes.
    *   **Mandatory:** Run `python3 17_scripts/audit_classifications.py` to ensure no layer-boundary violations.
    *   Audit findings land in `14_data/runs/classification_audit/`.

## Important Links

*   [Architecture Overview](ARCHITECTURE.md)
*   [Repository Structure](REPO_STRUCTURE.md)
*   [Data Model](DATA_MODEL.md)
*   [Services](SERVICES.md)
*   [Collaboration Guidelines](COLLABORATION.md)
