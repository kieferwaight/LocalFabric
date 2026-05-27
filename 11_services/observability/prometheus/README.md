# Prometheus

## Purpose

Metrics collection and local time-series storage for service observability.

## Container

- Image: `prom/prometheus`
- Compose file: `docker-compose.yml`

## Storage

- `./config/prometheus.yml` -> `/etc/prometheus/prometheus.yml:ro`: scrape configuration
- `${DATA_PATH}` -> `/prometheus`: Prometheus TSDB data

Bind to a data instance under `14_data/apps/prometheus/<name>/`.

## Ports

| Host env var      | Default | Container | Use               |
| ----------------- | ------: | --------: | ----------------- |
| `PROMETHEUS_PORT` |  `9090` |    `9090` | Prometheus UI/API |

## Run

```bash
cmd prometheus ./14_data/apps/prometheus/main
```

Or directly:

```bash
DATA_PATH=./14_data/apps/prometheus/main docker compose up -d
docker compose logs -f
docker compose down
```

## Notes

- Add scrape targets in `config/prometheus.yml`.
