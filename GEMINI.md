# LocalFabric Gemini Instructions

Welcome to the LocalFabric development environment. This document provides foundational guidance for AI agents working in this repository.

## Core Philosophy

LocalFabric is a **local-first, hybrid-ready** AI orchestration platform. Our goal is to provide a unified, provider-agnostic layer over models, tools, and services while maintaining portability and reproducibility.

## Architectural Mandates

1.  **Responsibility-Driven Classification:** All code must live in the correct numeric bucket under `20_workspaces/` as defined in `REPO_STRUCTURE.md`.
2.  **Strict Layer Separation:**
    *   **Adapters** translate interfaces to internal schemas (stateless).
    *   **Harnesses** manage execution lifecycle (retries, streaming, logging).
    *   **Drivers** provide storage access (normalize backend differences).
    *   **Workflows** orchestrate multi-step logic using harnesses and tools.
3.  **Local-First Execution:** Prefer local models (Ollama, LM Studio) and storage (SQLite, DuckDB) unless remote providers are explicitly required.
4.  **Deterministic Data Model:** All persistent state must live under `20_workspaces/14_data/` and be path-addressable.

## Development Workflow

1.  **Research:** Use `grep_search` and `glob` to map the codebase. Understand the classification bucket you are working in.
2.  **Strategy:** Draft a plan that respects the layered architecture.
3.  **Execution:** Apply surgical changes. Always use clean import names (e.g., `from core.paths import ...`).
4.  **Validation:**
    *   Run tests relevant to your changes.
    *   **Mandatory:** Run `python -m scripts.audit_classifications` (from `20_workspaces/17_scripts/`) to ensure no layer-boundary violations.
    *   Audit findings land in `14_data/runs/classification_audit/`.

## Important Links

*   [Architecture Overview](ARCHITECTURE.md)
*   [Repository Structure](REPO_STRUCTURE.md)
*   [Data Model](DATA_MODEL.md)
*   [Collaboration Guidelines](COLLABORATION.md)
*   [Workspace README](20_workspaces/README.md)
