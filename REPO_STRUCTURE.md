# Repository Structure

## Purpose

Defines the canonical folder structure, classification rules, and naming conventions for the repository.

All code and assets must conform to this layout to ensure consistency, discoverability, and agent-friendly generation.

## Root Layout

```text
.
|-- .github/
|   `-- PULL_REQUEST_TEMPLATE.md
|-- 00_planning/
|-- 10_todo/
|-- 20_workspaces/
|-- README.md
|-- SECURITY.md
|-- TESTING.md
|-- ARCHITECTURE.md
|-- COLLABORATION.md
|-- DATA_MODEL.md
|-- SERVICES.md
`-- REPO_STRUCTURE.md
```

## Workspaces Overview

All implementation lives under `20_workspaces/` using flat classification buckets.

```text
20_workspaces/
|-- 00_specs/
|-- 01_contracts/
|-- 02_core/
|-- 03_adapters/
|-- 04_harnesses/
|-- 05_router/
|-- 06_workflows/
|-- 07_tools/
|-- 08_drivers/
|-- 09_services/
|-- 10_service_runtime/
|-- 11_mcp/
|-- 12_prompts/
|-- 13_models/
|-- 14_data/
|-- 15_notebooks/
|-- 16_tests/
|-- 17_scripts/
|-- 18_docs/
`-- 19_archive/
```

## Classification Rules

### 1. Flat Structure

- Do not nest more deeply than two or three levels.
- Organize by responsibility type, not by project.
- Scale horizontally (more siblings) before vertically (deeper nesting).

Avoid:

```text
project/src/core/providers/adapters/...
```

Prefer:

```text
03_adapters/openai_compatible/ollama.py
04_harnesses/ollama/harness.py
```

This rule applies inside `14_data/` as well. Encode dimensions in **filenames**,
not in folders.

Avoid:

```text
14_data/logs/services/n8n/main/n8n.log
```

Prefer:

```text
14_data/logs/n8n-main.log
```

Run artifacts under `14_data/runs/<class>/<run-id>/` are the only place deeper
nesting is justified, because each run owns its own subtree of outputs. Cap it
at two levels under `runs/`.

### 2. Separation of Concerns

| Layer           | Responsibility                |
| --------------- | ----------------------------- |
| Adapters        | Interface translation         |
| Harnesses       | Execution and lifecycle       |
| Drivers         | Storage access                |
| Services        | Docker definitions            |
| Service Runtime | Execute services as tools     |
| Router          | Dispatch and decision making  |
| Workflows       | Multi-step orchestration      |
| Tools           | Reusable functional units     |

### 3. No Cross-Layer Leakage

- Adapters do not manage lifecycle.
- Harnesses do not implement storage logic.
- Drivers do not contain business logic.
- Workflows do not directly call external APIs; they use harnesses.

## Workspace Definitions

### `00_specs`

Agent-ready specifications and task artifacts.

```text
00_specs/
|-- 01_ideas/
|-- 02_research/
|-- 03_requirements/
|-- 04_tasks/
|-- 05_prompts/
`-- 06_final/
```

The numeric prefixes encode pipeline order: an idea is promoted left to right.
A spec's slug stays constant across stages — the same `<slug>.md` file appears
in each folder it has reached, so progress is observable by listing the slug
across folders.

### `01_contracts`

Shared schemas and interfaces.

```text
01_contracts/
|-- *.schema.json
`-- interfaces/
```

### `02_core`

Shared primitives and utilities.

```text
02_core/
`-- src/core/
```

Includes:

- Configuration
- Logging
- Environment management
- Error handling
- Subprocess utilities

### `03_adapters`

Interface translation layers.

```text
03_adapters/
|-- cli/
|-- openai_compatible/
|-- rest/
|-- mcp/
|-- langchain/
`-- shell/
```

Supported interface types:

- CLI
- OpenAI-compatible API
- REST
- MCP
- Subprocess, standard input, and standard output
- Docker CLI

### `04_harnesses`

Execution and lifecycle control.

```text
04_harnesses/
|-- claude/
|-- codex/
|-- gemini/
|-- openai/
|-- lmstudio/
|-- ollama/
`-- docker_service/
```

Each harness must implement:

```text
start()
stop()
status()
invoke()
stream()
logs()
health()
```

### `05_router`

Routing and decision system.

```text
05_router/
|-- router.py
|-- dispatcher.py
|-- classifier.py
|-- scorer.py
|-- policy.py
`-- routing_rules.yaml
```

### `06_workflows`

LangGraph and LangChain workflows.

```text
06_workflows/
|-- langgraph/
|-- langchain/
`-- shell/
```

### `07_tools`

Reusable task-level tools.

```text
07_tools/
|-- files/
|-- pdf/
|-- image/
|-- embeddings/
|-- browser/
`-- shell/
```

### `08_drivers`

Storage and database connectors.

```text
08_drivers/
|-- file/
|-- sql/
|-- vector/
|-- search/
|-- graph/
|-- cache/
`-- object/
```

### `09_services`

Docker Compose service catalog.

```text
09_services/
|-- ai/
|-- databases/
|-- vector/
|-- search/
|-- graph/
|-- auth/
|-- observability/
|-- document/
`-- workers/
```

### `10_service_runtime`

Execute services as command-line tools.

```text
10_service_runtime/
|-- cmd.py
|-- launcher.py
|-- resolver.py
`-- commands/
```

Command pattern:

```bash
cmd <service> <data-path>
```

### `11_mcp`

MCP servers, tools, and resources.

```text
11_mcp/
|-- servers/
|-- tools/
`-- resources/
```

### `12_prompts`

Prompt templates and roles.

```text
12_prompts/
|-- roles/
|-- tasks/
|-- agents/
`-- templates/
```

### `13_models`

Model registry and configuration.

```text
13_models/
|-- registry.yaml
|-- providers.yaml
|-- local/
|-- cloud/
`-- profiles/
```

### `14_data`

All persistent data.

```text
14_data/
|-- files/
|-- stores/
|-- apps/
|-- runs/
|-- logs/
|-- runtime/
`-- cache/
```

#### Data Model

| System        | Representation |
| ------------- | -------------- |
| SQLite        | File           |
| DuckDB        | File           |
| Postgres      | Folder         |
| Chroma/Qdrant | Folder         |
| OpenSearch    | Folder         |
| Neo4j         | Folder         |
| Applications  | Folder         |

### `15_notebooks`

Exploration and experiments.

### `16_tests`

Integration and contract tests.

### `17_scripts`

Utility and maintenance scripts.

### `18_docs`

Supporting documentation.

### `19_archive`

Deprecated or unused components.

## Naming Conventions

| Type     | Pattern                       |
| -------- | ----------------------------- |
| Adapter  | `*_adapter.py`                |
| Harness  | `harness.py` or `*_harness.py` |
| Driver   | `*_driver.py`                 |
| Workflow | `*_graph.py`                  |
| Schema   | `*.schema.json`               |
| Config   | `*.yaml`                      |

## Service Execution Model

All services are treated as executable units:

```bash
cmd postgres ./14_data/stores/postgres/research
cmd chromadb ./14_data/stores/chromadb/docs
cmd openwebui ./14_data/apps/openwebui/main
```

## Design Principles

- Flat over nested
- Classification over project grouping
- Strong separation of concerns
- Provider-agnostic interfaces
- Services treated as tools
- Data treated as addressable units
- Reproducible execution
- Agent-friendly structure

## Anti-Patterns

Avoid:

- Deep nesting beyond three levels.
- Mixing adapters and harnesses.
- Embedding business logic in drivers.
- Direct API calls inside workflows.
- Project-based folder grouping.

## Migration Rule

When adding new code:

1. Identify responsibility, such as adapter, harness, or driver.
2. Place it in the correct workspace bucket.
3. Follow naming conventions.
4. Avoid creating new top-level categories unless necessary.
