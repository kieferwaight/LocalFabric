# Traefik

## Purpose

Reverse proxy scaffold for routing, TLS termination, and local service fronting.

## Container

- Image: `traefik:v3`
- Compose file: `docker-compose.yml`

## Storage

- `./config` -> `/etc/traefik:ro`: local Traefik configuration
- Docker socket is mounted read-only for Docker provider discovery

## Ports

| Host env var | Default | Container | Use |
| --- | ---: | ---: | --- |
| `TRAEFIK_HTTP_PORT` | `80` | `80` | HTTP entrypoint |
| `TRAEFIK_HTTPS_PORT` | `443` | `443` | HTTPS entrypoint |
| `TRAEFIK_DASHBOARD_PORT` | `8080` | `8080` | Dashboard |

## Run

```bash
docker compose up -d
docker compose logs -f
docker compose down
```

## Notes

- Dashboard is insecure by default for local development.
- Add static/dynamic config under `./config` as routing needs firm up.
