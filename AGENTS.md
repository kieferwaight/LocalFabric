# AGENTS.md

## Scope

These instructions apply to the entire LocalFabric repository. Before making
changes, read `COLLABORATION.md` and work on a fresh provider branch in the
assigned worktree. The repository-specific branch convention takes precedence:
Codex work uses `codex_<type>_<short-description>`.

## Project Overview

LocalFabric is a local-first AI orchestration workspace for model harnesses,
tools, workflows, storage drivers, Docker-backed services, and agent-facing
interfaces. Python implementation and runtime assets are organized under
`20_workspaces/` by responsibility rather than feature.

Read these documents when a change touches their concern:

| Document | Use It For |
| --- | --- |
| `README.md` | Platform orientation and primary entry points |
| `ARCHITECTURE.md` | Execution layers, contracts, and system flow |
| `REPO_STRUCTURE.md` | Bucket ownership and classification rules |
| `DATA_MODEL.md` | Persistent data placement and addressing |
| `SERVICES.md` | Service conventions, including host-launched processes, log paths, and PID locations |
| `COLLABORATION.md` | Worktrees, branches, commits, and pull requests |
| `20_workspaces/README.md` | Imports, bucket map, and development commands |

## Workspace Map

| Path | Responsibility |
| --- | --- |
| `20_workspaces/01_contracts/` | Shared schemas and protocol definitions |
| `20_workspaces/02_core/` | Shared configuration, logging, and path primitives |
| `20_workspaces/03_adapters/` | Thin CLI/API/MCP interface translation |
| `20_workspaces/04_harnesses/` | Provider and service execution lifecycle |
| `20_workspaces/05_router/` | Classification, scoring, and dispatch |
| `20_workspaces/06_workflows/` | Multi-step orchestration |
| `20_workspaces/07_tools/` | Reusable provider-neutral capabilities |
| `20_workspaces/08_drivers/` | Filesystem, database, cache, and vector access |
| `20_workspaces/09_services/` | Self-contained Docker Compose service catalog |
| `20_workspaces/10_service_runtime/` | Service/data-path resolution CLI |
| `20_workspaces/11_mcp/` | MCP exposure layer, imported as `mcp_servers` |
| `20_workspaces/12_prompts/` | Prompt assets, not executable provider clients |
| `20_workspaces/13_models/` | Model registry and profiles |
| `20_workspaces/14_data/` | Persistent state and generated run artifacts |
| `20_workspaces/16_tests/` | Tests |
| `20_workspaces/17_scripts/` | Audits and maintenance utilities |
| `20_workspaces/18_docs/` | Supporting implementation documentation |
| `20_workspaces/19_archive/` | Retained legacy code, not active implementation |

## Engineering Rules

- Keep changes in the bucket that owns the responsibility. Adapters translate;
  harnesses invoke providers and control lifecycle; workflows orchestrate;
  tools stay reusable and provider-neutral; drivers own persistence.
- Import buckets through their configured Python package names, such as
  `core`, `adapters`, `harnesses`, `drivers`, `service_runtime`, and
  `mcp_servers`. Do not import by numeric directory name.
- Use `core.paths.WORKSPACES_ROOT` for implementation path resolution. Do not
  add competing repository-root calculations in new application code.
- Store persistent service and workflow data below `20_workspaces/14_data/`.
  Treat existing audit outputs there as tracked project artifacts and change
  them only when intentionally rerunning or documenting an audit.
- Keep service definitions self-contained under `09_services/<category>/<name>/`.
  Persistent mounts must be supplied through `DATA_PATH`; avoid hardcoded
  local state paths in Compose definitions.
- Do not build new work in `00_workspaces_backup/` or `19_archive/`.
- Keep local agent caches and worktree-specific overrides untracked. Root
  shared guidance files such as `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, and
  `SKILL.md` may be committed when intentionally added.

## Development Commands

Run Python commands from `20_workspaces/` unless noted otherwise:

```bash
cd 20_workspaces
python3 -m pip install -e '.[dev]'
python3 -m pytest
python3 -m adapters.cli.main --help
python3 -m mcp_servers.server
```

Use the checks appropriate to the changed area:

```bash
# Classification-sensitive changes; this refreshes tracked audit artifacts.
cd 20_workspaces
python3 17_scripts/audit_classifications.py

# Docker service catalog changes; requires Docker Compose.
cd 20_workspaces
./17_scripts/test-compose-configs.sh
```

For narrow changes, run focused tests first (for example,
`python3 -m pytest 16_tests/service_runtime/test_cmd.py`) and run the broader
suite before proposing behavior-affecting changes.

## Contribution Workflow

1. Work only in the assigned provider worktree and create a fresh scoped
   branch from the detached `main` baseline.
2. Keep the branch limited to the assigned prompt and update documentation or
   tests alongside behavior when needed.
3. Review ownership boundaries against `REPO_STRUCTURE.md`; for boundary
   changes, run the classification audit and inspect its output.
4. Run focused validation and record what passed or what could not be run.
5. Commit the intended changes and push the scoped branch to `origin`.
6. Open a pull request to `main` using the repository template, including
   purpose, assigned prompt, work summary, approach, validation, and risks or
   follow-ups.

A task is complete only when its branch has been pushed and its pull request
has been opened, unless the assigned prompt explicitly says not to publish or
publishing is blocked. If blocked, report the exact failure and needed next
action instead of describing the task as complete.
