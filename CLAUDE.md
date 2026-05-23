# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Shape

LocalFabric is a local-first AI orchestration workspace. All implementation lives under [`20_workspaces/`](20_workspaces/) in numeric-prefixed responsibility buckets (`01_contracts`, `02_core`, `03_adapters`, …, `19_archive`). The root holds only design docs ([ARCHITECTURE.md](ARCHITECTURE.md), [DATA_MODEL.md](DATA_MODEL.md), [REPO_STRUCTURE.md](REPO_STRUCTURE.md), [SERVICES.md](SERVICES.md), [COLLABORATION.md](COLLABORATION.md)) — read these before making cross-bucket changes.

**Working directory for every command below is `20_workspaces/`**, not the repo root. [pyproject.toml](20_workspaces/pyproject.toml), [conftest.py](20_workspaces/conftest.py), and the test root all live there.

## Numeric Bucket → Python Import Name

The numeric prefixes are filesystem-only — Python rejects module names starting with a digit. Clean import names are registered two ways: `[tool.setuptools.package-dir]` in [pyproject.toml](20_workspaces/pyproject.toml) (active after `pip install -e .`) and [conftest.py](20_workspaces/conftest.py) (active during pytest, no install needed). The two **must stay in sync**.

| Bucket dir | Import as |
|---|---|
| `02_core/src/core` | `core` |
| `03_adapters` | `adapters` |
| `04_harnesses` | `harnesses` |
| `05_router` | `router` |
| `06_workflows` | `workflows` |
| `07_tools` | `tools` |
| `08_drivers` | `drivers` |
| `10_service_runtime` | `service_runtime` |
| `11_mcp` | **`mcp_servers`** (not `mcp`) |

`11_mcp/` is deliberately exposed as `mcp_servers` because [11_mcp/server.py](20_workspaces/11_mcp/server.py) imports `from mcp.server.fastmcp import FastMCP` — the PyPI MCP SDK owns the `mcp` top-level name and we don't shadow it.

Always import via the clean name (`from drivers.sql.session import init_db`), never via the numeric path.

## Commands

```bash
cd 20_workspaces

# Install (writes import aliases into a .pth in site-packages)
pip install -e .
pip install -e ".[dev]"           # adds pytest, ruff, mypy
pip install -e ".[vision,pdf,vector]"   # optional capability deps

# Tests (also works without install — conftest.py registers aliases)
pytest
pytest 16_tests/drivers           # single bucket
pytest 16_tests/path/to/test_file.py::test_name   # single test

# Lint / type-check
ruff check .
mypy .

# Entry points
python -m adapters.cli.main --help
python -m mcp_servers.server
python -m service_runtime.cmd up postgres ./14_data/stores/postgres/research

# Classification audit — run before opening a PR
python3 17_scripts/audit_classifications.py
# Findings land at: 14_data/runs/classification_audit/findings.jsonl
```

## Architecture (what to know before editing)

Execution flows **Interface → Router → Workflow (optional) → Harness → Adapter → Provider/Service/Tool → Driver → Data Layer (`14_data/`)**. The layer responsibilities are enforced by the classification audit:

- **Adapters** translate interfaces (CLI/REST/OpenAI-compat/MCP) into internal schema. Stateless. No lifecycle, no health probes.
- **Harnesses** own execution lifecycle: invoke/stream/retry/logs/health. Docker lifecycle lives in `harnesses.docker_service`, not in the service runtime.
- **Drivers** own all persistent file I/O and storage access. Workflows must delegate writes to drivers (rule: `workflow_owns_persistent_file_io`).
- **Workflows** orchestrate; they call harnesses/tools, never external APIs directly, and don't execute prompt assets as scripts.
- **Router** dispatches internal capabilities. Must not import from `11_mcp` (exposure layer).
- **`02_core`** stays domain-neutral — no document/PDF/etc. tool execution.
- **`11_mcp`** is a thin exposure shim. Don't combine provider call + prompt + fetch in one MCP tool.
- **`12_prompts`** holds templates only — no API clients.
- **`13_models`** is authoritative for which models are available; configured models must appear in the registry.

Full rule list in [20_workspaces/18_docs/classification_audit.md](20_workspaces/18_docs/classification_audit.md). The audit emits JSONL findings with stable IDs; rerunning preserves `status` on still-present findings.

## Path & Data Conventions

- **`core.paths.WORKSPACES_ROOT`** is the only canonical path anchor. Never use `os.path.join(__file__, "..", "..")` to climb out of a bucket — import from `core.paths` instead. Honors the `WORKSPACES_ROOT` env var for relocating the tree (tests use this).
- All persistent state lives under `20_workspaces/14_data/` and is addressed as `<type>://<path>` (e.g. `postgres://14_data/stores/postgres/research`). See [DATA_MODEL.md](DATA_MODEL.md).
- Services are addressed by data path: `cmd <service> <data-path>`. Docker Compose definitions are in `09_services/<category>/<service>/`, all volumes must bind through `${DATA_PATH}`.
- Safe to delete: `14_data/cache/`, `14_data/runs/`. Persistent: `14_data/stores/`, `14_data/apps/`.

## Worktree & Branch Workflow

This repo uses per-provider Git worktrees (see [COLLABORATION.md](COLLABORATION.md)). The Claude worktree is `~/agents/claude/LocalFabric`. **Work only in this worktree.** Do not touch sibling worktrees at `~/agents/{codex,copilot,gemini}/LocalFabric`.

Every Claude branch must match `claude_<type>_<short-description>` where `<type>` is one of `feature | bug | docs | refactor | test | chore | audit`. Start each new assignment from a detached-main baseline:

```bash
git switch --detach main
git switch -c claude_<type>_<short-description>
```

Do not implement on `main`, do not reuse an old branch for a new prompt, and rebase `main` into a long-running branch before opening a PR. Pull requests target `main` and must keep the [.github/PULL_REQUEST_TEMPLATE.md](.github/PULL_REQUEST_TEMPLATE.md) fields (Purpose, Assigned Prompt, Approach, Validation, Risks/Follow-ups).

## Before Opening a PR

1. Run focused tests for the touched buckets.
2. Run `python3 17_scripts/audit_classifications.py` and confirm no new findings (or document why they're intentional).
3. Fill out every PR template field — the Assigned Prompt is required, not optional.
