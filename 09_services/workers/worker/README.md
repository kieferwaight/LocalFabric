# Worker Service

## Purpose

Background worker scaffold for extraction, embeddings, parsing, graph writes, and
pipeline jobs.

## Container

- Image: `contentgraph-worker:local`
- Build context: `.`
- Compose file: `docker-compose.yml`

## Storage

- `${DATA_PATH}` -> `/work`: local scratch workspace
- Application code lives in `./app`

Bind to a data instance under `14_data/runs/workers/contentgraph/<name>/`.

## Ports

| Host env var | Default | Container | Use |
| --- | ---: | ---: | --- |
| none | n/a | n/a | Worker has no exposed port |

## Required Environment

| Var | Description |
| --- | --- |
| `DATABASE_URL` | Postgres connection string (e.g. `postgresql://user:pass@pgvector:5432/contentgraph`) |

## Run

```bash
DATA_PATH=./14_data/runs/workers/contentgraph/main \
  DATABASE_URL=postgresql://postgres:<secret>@pgvector:5432/contentgraph \
  docker compose up -d --build
docker compose logs -f
docker compose down
```

## Notes

- Environment variables point to conventional service hostnames and can be edited per stack.
- Secrets must be supplied via the environment; no defaults are embedded in compose.
- The placeholder worker loops until replaced with real job logic.
