# Temporal

## Purpose

Durable workflow engine for ingestion and extraction pipelines.

## Container

- Image: `temporalio/auto-setup`
- Compose file: `docker-compose.yml`

## Storage

- `./dynamicconfig` -> `/etc/temporal/config/dynamicconfig`: local Temporal dynamic config
- Workflow history is stored in the configured database, not this folder

## Ports

| Host env var    | Default | Container | Use               |
| --------------- | ------: | --------: | ----------------- |
| `TEMPORAL_PORT` |  `7233` |    `7233` | Temporal frontend |

## Required Environment

| Var                 | Description                          |
| ------------------- | ------------------------------------ |
| `POSTGRES_USER`     | Postgres user for Temporal state     |
| `POSTGRES_PASSWORD` | Postgres password for Temporal state |
| `POSTGRES_SEEDS`    | Postgres host (default `pgvector`)   |
| `DB_PORT`           | Postgres port (default `5432`)       |

## Run

```bash
POSTGRES_USER=postgres POSTGRES_PASSWORD=<secret> POSTGRES_SEEDS=pgvector \
  docker compose up -d
docker compose logs -f
docker compose down
```

## Notes

- Expects PostgreSQL-compatible storage at host `pgvector` by default.
- For a fully standalone Temporal setup, add a database service to this folder.
