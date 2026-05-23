# PostgreSQL

## Purpose

Canonical relational store for metadata, ingestion state, file records, hashes,
and jobs. This plain Postgres scaffold is an alternative to pgvector.

## Container

- Image: `postgres:16`
- Compose file: `docker-compose.yml`

## Storage

- `${DATA_PATH}` -> `/var/lib/postgresql/data`: PostgreSQL data directory

Bind to a data instance under `14_data/stores/postgres/<name>/`.

## Ports

| Host env var | Default | Container | Use |
| --- | ---: | ---: | --- |
| `POSTGRES_PORT` | `5433` | `5432` | PostgreSQL client traffic |

## Required Environment

| Var | Description |
| --- | --- |
| `POSTGRES_USER` | Superuser name |
| `POSTGRES_PASSWORD` | Superuser password |
| `POSTGRES_DB` | Initial database (default `contentgraph`) |

## Run

```bash
cmd postgres ./14_data/stores/postgres/research
```

Or directly:

```bash
DATA_PATH=./14_data/stores/postgres/research \
  POSTGRES_USER=postgres POSTGRES_PASSWORD=postgres POSTGRES_DB=contentgraph \
  docker compose up -d
docker compose logs -f
docker compose down
```

## Notes

- Uses host port `5433` so pgvector can use `5432`.
- Credentials must be supplied via environment; no defaults are embedded in compose.
