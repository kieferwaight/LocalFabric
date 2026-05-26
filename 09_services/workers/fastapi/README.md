# FastAPI App

## Purpose

API gateway scaffold for graph queries, search, ingestion endpoints, and service
integration experiments.

## Container

- Image: `contentgraph-api:local`
- Build context: `.`
- Compose file: `docker-compose.yml`

## Storage

- Application code lives in `./app`
- No durable service data is configured

## Ports

| Host env var   | Default | Container | Use      |
| -------------- | ------: | --------: | -------- |
| `FASTAPI_PORT` |  `8000` |    `8000` | HTTP API |

## Required Environment

| Var              | Description                |
| ---------------- | -------------------------- |
| `DATABASE_URL`   | Postgres connection string |
| `NEO4J_PASSWORD` | Neo4j password             |

## Run

```bash
DATABASE_URL=postgresql://postgres:<secret>@pgvector:5432/contentgraph \
  NEO4J_PASSWORD=<secret> \
  docker compose up -d --build
docker compose logs -f
docker compose down
```

## Notes

- Health check endpoint: `GET /health`
- Environment variables point to conventional service hostnames and can be edited per stack.
- Secrets must be supplied via the environment; no defaults are embedded in compose.
