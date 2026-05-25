# Data Model

## Purpose

Defines how data is structured, stored, addressed, and accessed across the system.

The goal is to provide a uniform abstraction over heterogeneous storage systems while maintaining portability, locality, and reproducibility.

## Core Principles

- Treat all storage systems as addressable data targets.
- Normalize interaction via drivers.
- Prefer filesystem-backed persistence.
- Maintain human-readable structure where possible.
- Avoid hidden or implicit state.
- Ensure reproducibility via path-based addressing.

## Data Target Abstraction

All storage systems are represented as one of the following:

| Type            | Representation                     |
| --------------- | ---------------------------------- |
| File-based      | Single file                        |
| Directory-based | Folder                             |
| Service-backed  | Folder mapped to a container volume |

## Canonical Data Root

All persistent data lives under `14_data/`.

## Top-Level Structure

```text
14_data/
|-- _registry/
|-- files/
|-- stores/
|-- apps/
|-- runs/
|-- logs/
|-- runtime/
`-- cache/
```

Each top-level bucket is a single classification of state. Do not introduce
new top-level folders unless an existing one cannot represent the data without
distorting its semantics. See [REPO_STRUCTURE.md](REPO_STRUCTURE.md) for the
flat-structure rule that applies inside every bucket below.

## 1. Registry

Metadata describing all data targets.

```text
_registry/
|-- stores.yaml
|-- services.yaml
|-- mounts.yaml
`-- secrets.example.env
```

### Responsibilities

- Track logical names to physical paths.
- Track service bindings.
- Store environment templates.
- Enable discovery by routers and harnesses.

## 2. Files

Unstructured or semi-structured file storage.

```text
files/
|-- inbox/
|-- processed/
|-- exports/
`-- archive/
```

### Usage

- Input ingestion
- Intermediate artifacts
- Exported results
- Long-term storage

## 3. Stores

Primary structured data systems.

```text
stores/
|-- sqlite/
|-- duckdb/
|-- postgres/
|-- chromadb/
|-- qdrant/
|-- opensearch/
|-- neo4j/
`-- redis/
```

### 3.1 Store Types

#### SQLite and DuckDB

```text
sqlite/
`-- research.sqlite
duckdb/
`-- analytics.duckdb
```

- Single-file databases
- Portable
- Preferred for local workflows

#### Postgres

```text
postgres/
|-- research/
`-- agents/
```

Each folder represents:

- A full database instance
- Storage backed by a Docker volume

#### Vector Stores

```text
chromadb/
`-- research/
qdrant/
`-- codebase/
```

- Folder-backed persistent indices
- Used for embeddings and retrieval

#### Search

```text
opensearch/
`-- content-search/
```

- Index data persisted through a container volume

#### Graph

```text
neo4j/
`-- content-graph/
```

- Graph database persisted as a directory

#### Cache

```text
redis/
`-- cache-main/
```

- Ephemeral or semi-persistent
- May be cleared without affecting system integrity

## 4. Applications

Application-level state.

```text
apps/
|-- openwebui/
|-- grafana/
|-- prometheus/
|-- keycloak/
`-- minio/
```

Each folder represents:

- One application instance
- Fully self-contained state

## 5. Runs

Execution artifacts.

```text
runs/
|-- workflows/
|-- agents/
|-- evaluations/
`-- service-tests/
```

### Characteristics

- Time-scoped
- Reproducible inputs and outputs
- Used for debugging and evaluation

## 6. Logs

Captured stdout, stderr, and rotated log output from services, harnesses, and
workflows.

```text
logs/
|-- <service>-<instance>.log
|-- <service>-<instance>.err
|-- <harness>-<run>.log
`-- <workflow>-<run>.log
```

### Conventions

- One file per `(producer, instance)` pair. Encode the producer kind and
  instance name in the filename — do not create per-producer subfolders.
- When a producer needs many files (rotation, separate streams), allow at most
  one level of nesting: `logs/<service>-<instance>/<file>`.
- Filenames are kebab-case and time-sortable. Rotated files use a date suffix:
  `n8n-main.20260524.log`.
- Logs are regenerable and safe to delete when the producer is stopped.

## 7. Runtime

Live process state for host-launched services and background processes.

```text
runtime/
|-- <service>-<instance>.pid
|-- <service>-<instance>.lock
`-- <service>-<instance>.sock
```

### Characteristics

- Points to a live process or holds a process-scoped lease.
- Regenerated on every start; meaningless after the producer exits.
- Distinct from `runs/` (time-scoped artifacts) and `cache/` (regenerable
  outputs). PIDs and lockfiles are neither artifacts nor outputs.
- Safe to delete when no producer is running. A stale `.pid` should be removed,
  not preserved.

Host-launched processes (npx, uvicorn, `python -m`, etc.) must write their PID
files here. See [SERVICES.md](SERVICES.md) for the launcher contract.

## 8. Cache

Non-critical, regenerable data.

```text
cache/
|-- models/
|-- downloads/
`-- temp/
```

## Addressing Model

All data targets are referenced using:

```text
<type>://<path>
```

Examples:

```text
sqlite://14_data/stores/sqlite/research.sqlite
postgres://14_data/stores/postgres/research
chromadb://14_data/stores/chromadb/docs
file://14_data/files/inbox/document.pdf
```

## Service Mapping

Each directory-backed system maps to a service instance. For example:

```bash
cmd postgres ./14_data/stores/postgres/research
cmd chromadb ./14_data/stores/chromadb/docs
cmd openwebui ./14_data/apps/openwebui/main
```

## Logical vs. Physical Separation

| Layer     | Role                          |
| --------- | ----------------------------- |
| Logical   | Named data targets (registry) |
| Physical  | Filesystem paths              |
| Execution | Services bound to paths       |

## Driver Responsibility

Drivers must:

- Accept path-based targets.
- Initialize storage if missing.
- Normalize read, write, and query operations.
- Hide backend-specific complexity.

## Naming Conventions

| Resource           | Convention                  |
| ------------------ | --------------------------- |
| SQLite file        | `<name>.sqlite`             |
| DuckDB file        | `<name>.duckdb`             |
| Folder-based store | `<name>/`                   |
| Run folder         | `<timestamp>-<name>/`       |
| Cache folder       | Descriptive and disposable  |

## Lifecycle

### Creation

- Created on first access through a driver or service runtime.
- Initialized with default schema and configuration.

### Usage

- Accessed through drivers or harnesses.
- Never directly manipulated unless necessary.

### Destruction

Safe to delete:

- `cache/`
- `runs/`
- `logs/`
- `runtime/` (only when the producer is not running)

Persistent:

- `stores/`
- `apps/`

## Data Portability

All data must be:

- Copyable through the filesystem.
- Independent of the host machine.
- Re-creatable through services and drivers.

## Anti-Patterns

Avoid:

- Storing data outside `14_data/`.
- Embedding absolute paths in code.
- Mixing multiple data systems in one folder.
- Hidden state inside containers.
- Non-deterministic file naming.

## Future Extensions

- Versioned datasets
- Snapshot and restore system
- Data lineage tracking
- Cross-store indexing
- Remote storage backends
- Distributed data replication
