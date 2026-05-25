# pgvector

## Purpose

Postgres with vector extension support. Use this instead of plain Postgres when
embedding vectors stay in PostgreSQL.

## Container

- Image: `pgvector/pgvector:pg16`
- Compose file: `docker-compose.yml`

## Storage

- `${DATA_PATH}` -> `/var/lib/postgresql/data`: PostgreSQL data directory
- `./init` -> `/docker-entrypoint-initdb.d:ro`: initialization SQL, including `CREATE EXTENSION vector`

Bind to a data instance under `14_data/stores/pgvector/<name>/`.

## Ports

| Host env var | Default | Container | Use |
| --- | ---: | ---: | --- |
| `PGVECTOR_PORT` | `5432` | `5432` | PostgreSQL client traffic |

## Required Environment

| Var | Description |
| --- | --- |
| `POSTGRES_USER` | Superuser name |
| `POSTGRES_PASSWORD` | Superuser password |
| `POSTGRES_DB` | Initial database (default `contentgraph`) |

## Run

```bash
cmd pgvector ./14_data/stores/pgvector/research
```

Or directly:

```bash
DATA_PATH=./14_data/stores/pgvector/research \
  POSTGRES_USER=postgres POSTGRES_PASSWORD=postgres POSTGRES_DB=contentgraph \
  docker compose up -d
docker compose logs -f
docker compose down
```

## Notes

- Preferred relational database scaffold for the content graph MVP.
- Credentials must be supplied via environment; no defaults are embedded in compose.
