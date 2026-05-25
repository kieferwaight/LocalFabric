# Grafana

## Purpose

Dashboard UI for metrics and observability data.

## Container

- Image: `grafana/grafana`
- Compose file: `docker-compose.yml`

## Storage

- `${DATA_PATH}` -> `/var/lib/grafana`: Grafana database, dashboards, and plugins

Bind to a data instance under `14_data/apps/grafana/<name>/`.

## Ports

| Host env var | Default | Container | Use |
| --- | ---: | ---: | --- |
| `GRAFANA_PORT` | `3002` | `3000` | Grafana UI |

## Required Environment

| Var | Description |
| --- | --- |
| `GF_SECURITY_ADMIN_USER` | Initial admin username |
| `GF_SECURITY_ADMIN_PASSWORD` | Initial admin password |

## Run

```bash
cmd grafana ./14_data/apps/grafana/main
```

Or directly:

```bash
DATA_PATH=./14_data/apps/grafana/main \
  GF_SECURITY_ADMIN_USER=admin GF_SECURITY_ADMIN_PASSWORD=<strong-password> \
  docker compose up -d
docker compose logs -f
docker compose down
```

## Notes

- Host port defaults to `3002` to avoid Gitea.
- Credentials must be supplied via environment; no defaults are embedded in compose.
