# Neo4j

## Purpose

Main graph store for folders, files, links, ACL relationships, dependencies, and
graph traversal workloads.

## Container

- Image: `neo4j:5`
- Compose file: `docker-compose.yml`

## Storage

- `${DATA_PATH}/data` -> `/data`: graph database
- `${DATA_PATH}/logs` -> `/logs`: Neo4j logs
- `${DATA_PATH}/import` -> `/var/lib/neo4j/import`: CSV/import staging
- `${DATA_PATH}/plugins` -> `/plugins`: local plugins

Bind to a data instance under `14_data/stores/neo4j/<name>/`.

## Ports

| Host env var | Default | Container | Use |
| --- | ---: | ---: | --- |
| `NEO4J_HTTP_PORT` | `7474` | `7474` | Browser/admin UI |
| `NEO4J_BOLT_PORT` | `7687` | `7687` | Bolt driver traffic |

## Required Environment

| Var | Description |
| --- | --- |
| `NEO4J_USER` | Neo4j user (default `neo4j`) |
| `NEO4J_PASSWORD` | Neo4j password |

## Run

```bash
cmd neo4j ./14_data/stores/neo4j/content-graph
```

Or directly:

```bash
DATA_PATH=./14_data/stores/neo4j/content-graph \
  NEO4J_PASSWORD=<strong-password> \
  docker compose up -d
docker compose logs -f
docker compose down
```

## Notes

- Credentials must be supplied via environment; no defaults are embedded in compose.
- Increase heap settings in `docker-compose.yml` for larger graph loads.
