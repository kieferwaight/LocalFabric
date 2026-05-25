# 20_workspaces

Numeric-bucket layout per [REPO_STRUCTURE.md](../REPO_STRUCTURE.md),
[ARCHITECTURE.md](../ARCHITECTURE.md), [DATA_MODEL.md](../DATA_MODEL.md),
[SERVICES.md](../SERVICES.md). The pre-reclassification tree lives at
`00_workspaces_backup/` (read-only).

## Buckets

| Bucket | Role | Import name |
|--------|------|-------------|
| `00_specs/` | Agent-ready specs and task artifacts | — |
| `01_contracts/` | Shared JSON schemas and Protocol mirrors | — |
| `02_core/` | Shared primitives: config, logging, paths | `core` |
| `03_adapters/` | Interface translation (CLI, REST, OpenAI-compat, MCP) | `adapters` |
| `04_harnesses/` | Execution lifecycle per provider | `harnesses` |
| `05_router/` | Classification → scoring → dispatch | `router` |
| `06_workflows/` | LangGraph, LangChain, shell, YAML workflows | `workflows` |
| `07_tools/` | Reusable functional units (image, pdf, vision, embeddings, …) | `tools` |
| `08_drivers/` | Storage/database connectors | `drivers` |
| `09_services/` | Docker-Compose service catalog by category | — |
| `10_service_runtime/` | `cmd <service> <path>` runtime | `service_runtime` |
| `11_mcp/` | MCP servers and exposure shims | `mcp_servers` |
| `12_prompts/` | Prompt templates | — |
| `13_models/` | Model registry, providers, profiles | — |
| `14_data/` | Persistent data (filesystem-backed) | — |
| `15_notebooks/` | Exploration notebooks | — |
| `16_tests/` | Integration and contract tests | — |
| `17_scripts/` | Utility and maintenance scripts | — |
| `18_docs/` | Supporting docs | — |
| `19_archive/` | Deprecated components | — |

## Import-name strategy

The numeric prefixes are filesystem-only — Python forbids module names that
start with a digit. The buckets are registered with clean names via:

- **`pyproject.toml`** — `[tool.setuptools.package-dir]` maps each bucket to
  its import name. `pip install -e .` from this directory writes the
  aliases into a `.pth` file in site-packages and every `from harnesses.base
  import Harness` resolves naturally.
- **`conftest.py`** — registers the same aliases at pytest startup so the
  test suite runs without an install step.

`11_mcp/` is intentionally exposed as **`mcp_servers`**, not `mcp`:
`11_mcp/server.py` uses `from mcp.server.fastmcp import FastMCP` (the PyPI
MCP SDK), so we leave that top-level name unshadowed.

## Running

```bash
# from repo root
cd 20_workspaces
pip install -e .

# Tests (no install also works — conftest.py registers the aliases)
pytest

# CLI
python -m adapters.cli.main --help

# MCP server
python -m mcp_servers.server

# A service (Docker lifecycle goes through harnesses.docker_service)
python -m service_runtime.cmd up postgres ./14_data/stores/postgres/research
```

## Notes for contributors

- Cross-bucket imports use the clean import name (`from drivers.sql.session
  import init_db`), never the numeric path.
- `core.paths.WORKSPACES_ROOT` is the canonical anchor for path resolution —
  no `os.path.join(__file__, "..", "..")` patterns anywhere else.
- `17_scripts/audit_classifications.py` continuously checks for layer-boundary
  violations; run it before opening a PR. Findings land at
  `14_data/runs/classification_audit/`.
