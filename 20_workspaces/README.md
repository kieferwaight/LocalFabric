# 20_workspaces

Numeric-bucket layout per [REPO_STRUCTURE.md](../REPO_STRUCTURE.md),
[ARCHITECTURE.md](../ARCHITECTURE.md), [DATA_MODEL.md](../DATA_MODEL.md),
[SERVICES.md](../SERVICES.md). The legacy tree lives at `00_workspaces_backup/`.

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
| `10_service_runtime/` | `cmd <service> <path>` runtime | — |
| `11_mcp/` | MCP servers and tools | `mcp_layer` |
| `12_prompts/` | Prompt templates | — |
| `13_models/` | Model registry, providers, profiles | — |
| `14_data/` | Persistent data (filesystem-backed) | — |
| `15_notebooks/` | Exploration notebooks | — |
| `16_tests/` | Integration and contract tests | — |
| `17_scripts/` | Utility scripts | — |
| `18_docs/` | Supporting docs (incl. legacy snapshots) | — |
| `19_archive/` | Deprecated components | — |

## Import-name convention

Numeric-prefixed directory names (`02_core`, `04_harnesses`, …) are not valid
Python identifiers. Symlinks at this directory's root map clean Python package
names to their bucket:

```
core       -> 02_core/src/core
adapters   -> 03_adapters
harnesses  -> 04_harnesses
router     -> 05_router
workflows  -> 06_workflows
tools      -> 07_tools
drivers    -> 08_drivers
mcp_layer  -> 11_mcp
```

Note: `11_mcp` is exposed as **`mcp_layer`**, not `mcp`, to avoid colliding
with the PyPI `mcp` SDK that `11_mcp/servers/server.py` imports as
`mcp.server.fastmcp`.

Add `20_workspaces/` to `PYTHONPATH` (or run `pip install -e .` from this
directory) and every `from harnesses.base import Harness`, `from
drivers.sql.session import init_db`, `from tools.embeddings.query import
LocalKnowledgeQuery`, etc. resolves cleanly.

Tests pick this up automatically via `[tool.pytest.ini_options].pythonpath`
in `pyproject.toml`.

## Running

```bash
# from repo root
cd 20_workspaces
pip install -e .

# CLI (the migrated ai_utils Typer app)
python -m adapters.cli.main --help

# Tests
pytest 16_tests/

# A service (once 10_service_runtime/cmd.py is wired)
python -m service_runtime.cmd postgres ./14_data/stores/postgres/research
```

## Migration notes

This tree was generated from `00_workspaces_backup/` (formerly
`20_workspaces/`). See `18_docs/ai_utils_legacy.md` for the legacy README
plus a mapping of legacy paths to the new bucket locations. The backup is
preserved read-only — do not modify it.

The `core/paths.py` module was synthesized from caller usage during the
migration (the original `ai_utils.core.paths` module was referenced but
absent from the source tree). Worth a review pass.
