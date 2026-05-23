# Casbin Service

## Purpose

Simple authorization service scaffold for Casbin-based policy checks.

## Container

- Image: `contentgraph-casbin-service:local`
- Build context: `.`
- Compose file: `docker-compose.yml`

## Storage

- Application code lives in `./app`
- No durable service data is configured

## Ports

| Host env var | Default | Container | Use |
| --- | ---: | ---: | --- |
| `CASBIN_PORT` | `8090` | `8080` | HTTP API |

## Run

```bash
docker compose up -d --build
docker compose logs -f
docker compose down
```

## Notes

- Health check endpoint: `GET /health`
- Use this as a simpler alternative to OpenFGA when relationship modeling is not needed.
