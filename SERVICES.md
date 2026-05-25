# Services

## Purpose

Defines how infrastructure services are structured, configured, and executed.

Services are treated as portable, filesystem-backed execution units that can be launched, managed, and destroyed through a unified interface.

## Core Principles

- Services are stateless definitions with stateful data folders.
- All state is persisted under `14_data/`.
- Services are addressed by data path.
- Docker Compose is the execution backend.
- Services behave like command-line executable tools.

## Service Model

Each service consists of:

| Component  | Description                      |
| ---------- | -------------------------------- |
| Definition | Docker Compose template          |
| Runtime    | Generated instance configuration |
| Data       | Filesystem-backed state          |
| Interface  | CLI command (`cmd`)              |

## Service Catalog Location

Service definitions live under `09_services/`.

## Service Categories

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

## Example Service Definitions

### Database

```text
databases/
`-- postgres/
    |-- docker-compose.yml
    `-- README.md
```

### Vector Store

```text
vector/
`-- qdrant/
    |-- docker-compose.yml
    `-- README.md
```

### AI Runtime

```text
ai/
`-- ollama/
    |-- docker-compose.yml
    `-- README.md
```

## Service Runtime

All services are executed using:

```bash
cmd <service> <data-path>
```

Examples:

```bash
cmd postgres ./14_data/stores/postgres/research
cmd qdrant ./14_data/stores/qdrant/research
cmd ollama ./14_data/apps/ollama/main
cmd openwebui ./14_data/apps/openwebui/main
```

## Data Binding

Each service binds to a data directory.

| Service    | Data Path                    |
| ---------- | ---------------------------- |
| Postgres   | `stores/postgres/<name>/`    |
| Qdrant     | `stores/qdrant/<name>/`      |
| ChromaDB   | `stores/chromadb/<name>/`    |
| OpenSearch | `stores/opensearch/<name>/`  |
| Neo4j      | `stores/neo4j/<name>/`       |
| OpenWebUI  | `apps/openwebui/<name>/`     |

## Service Instance Model

Each invocation creates or uses an instance:

```text
14_data/
`-- stores/
    `-- postgres/
        `-- research/
            |-- data/
            |-- config/
            `-- logs/
```

## Runtime Responsibilities

The service runtime in `10_service_runtime/` must:

- Resolve the service definition.
- Bind volumes to a data path.
- Allocate ports.
- Generate environment variables.
- Render Compose overrides.
- Start and stop containers.
- Perform health checks.

## Compose Structure

Each service must include:

```yaml
version: "3.9"
services:
  <service-name>:
    image: <image>
    volumes:
      - ${DATA_PATH}:/data
    ports:
      - "${PORT}:<container-port>"
    environment:
      - ENV_VAR=value
```

## Required Conventions

### 1. Volume Binding

All persistent data must map through `${DATA_PATH}`.

### 2. No Hardcoded Paths

Avoid:

```yaml
volumes:
  - ./data:/var/lib/postgresql/data
```

Use:

```yaml
volumes:
  - ${DATA_PATH}:/var/lib/postgresql/data
```

### 3. Single Responsibility

Each service definition should:

- Represent one logical service.
- Avoid bundling unrelated services.
- Use dependencies only when required.

## Service Registry

The optional registry file is `14_data/_registry/services.yaml`.

Example:

```yaml
services:
  postgres:
    category: databases
    default_port: 5432
    data_subpath: stores/postgres
  qdrant:
    category: vector
    default_port: 6333
    data_subpath: stores/qdrant
```

## Lifecycle Commands

The runtime must support:

```bash
cmd start <service> <path>
cmd stop <service> <path>
cmd status <service> <path>
cmd logs <service> <path>
cmd destroy <service> <path>
```

## Instance Resolution

Resolution algorithm:

1. Identify the service definition in `09_services/`.
2. Resolve the data path.
3. Generate instance configuration.
4. Allocate ports.
5. Start containers.

## Port Allocation

Ports must:

- Be dynamically assigned or reserved.
- Avoid collisions.
- Be persisted per instance.

For example, allocations may be stored in `14_data/_registry/ports.yaml`.

## Environment Injection

Each service instance may include an `.env` file generated dynamically:

```dotenv
DATA_PATH=...
PORT=...
SERVICE_NAME=...
```

## Health Checks

Each service should expose:

- An HTTP endpoint, or
- A TCP readiness check.

The runtime must verify readiness before marking a service as ready.

## Logs

Service logs must be written under `14_data/logs/` as a single file per
`(service, instance)` pair:

```text
14_data/logs/<service>-<instance>.log
14_data/logs/<service>-<instance>.err   # optional, when stderr is separated
```

Do not create per-service subfolders. If a service produces multiple files
(rotation, multiple streams), use at most one level of nesting:
`14_data/logs/<service>-<instance>/`.

For Compose-managed services, the runtime is responsible for capturing the
container's stdout/stderr to this location.

## Runtime State

Host-launched processes (see below) must write their PID file to:

```text
14_data/runtime/<service>-<instance>.pid
```

Lock files and sockets follow the same pattern (`.lock`, `.sock`). PID files
are removed by the runtime when the service stops, and any stale PID file
should be deleted on next start.

## Host-Launched Services

Some services run directly on the host instead of in a container (npx,
`python -m`, `uvicorn`, native binaries). They use the **same data conventions
as Compose-managed services** and are started through the same
`cmd <service> <data-path>` interface.

### Conventions

- The launcher in [10_service_runtime/](10_service_runtime/)
  resolves the service definition, then launches the host process and captures
  output to `14_data/logs/<service>-<instance>.log`.
- The launcher writes `14_data/runtime/<service>-<instance>.pid` after fork.
- The launcher removes the PID file on clean shutdown and flags stale PID
  files (process gone, file present) on the next `cmd start`.
- Persistent state (databases, app data) still lives under
  `14_data/stores/<service>/<instance>/` or `14_data/apps/<service>/<instance>/`,
  not next to the binary.

### Anti-patterns

Do not write logs, PIDs, or other operational data to:

- The repository root (`./<service>/`)
- The current working directory of the launching process
- Any path outside `14_data/`

If a service definition does not yet exist in [09_services/](09_services/),
add one — even for host-launched processes — so the launcher and registry can
resolve it. A host-launched service is still a registered service.

## Service Composition

For multi-service setups:

```text
ai/
`-- open-webui/
    |-- docker-compose.yml
    `-- dependencies:
        `-- ollama
```

Dependencies should be:

- Explicit
- Minimal
- Optional when possible

## Extensibility

New services must:

1. Add a folder under the correct category.
2. Provide `docker-compose.yml`.
3. Follow volume and environment conventions.
4. Be discoverable by the runtime.

## Anti-Patterns

Avoid:

- Hardcoded ports.
- Hardcoded filesystem paths.
- Writing outside `DATA_PATH`.
- Mixing multiple services in one definition unnecessarily.
- Embedding secrets in Compose files.
- Stateful containers without volume binding.

## Design Summary

| Concept   | Description                         |
| --------- | ----------------------------------- |
| Service   | Docker-based executable unit        |
| Instance  | Service bound to a data path        |
| Runtime   | System that manages execution       |
| Data Path | Source of truth for state           |
| Command   | Unified interface to run services   |

## Future Extensions

- Remote service execution
- Kubernetes backend
- Service snapshots and restore
- Auto-scaling services
- Distributed service orchestration
- Service dependency graphs
