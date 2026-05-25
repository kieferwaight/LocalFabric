# OpenSearch

## Purpose

Full-text and keyword search store for extracted text, logs, and searchable file
metadata.

## Container

- Image: `opensearchproject/opensearch:2`
- Compose file: `docker-compose.yml`

## Storage

- `${DATA_PATH}` -> `/usr/share/opensearch/data`: OpenSearch index data

Bind to a data instance under `14_data/stores/opensearch/<name>/`.

## Ports

| Host env var | Default | Container | Use |
| --- | ---: | ---: | --- |
| `OPENSEARCH_PORT` | `9200` | `9200` | HTTP API |
| `OPENSEARCH_PERF_PORT` | `9600` | `9600` | Performance analyzer |

## Required Environment

| Var | Description |
| --- | --- |
| `OPENSEARCH_INITIAL_ADMIN_PASSWORD` | Initial admin password (must satisfy OpenSearch complexity rules) |

## Run

```bash
cmd opensearch ./14_data/stores/opensearch/content-search
```

Or directly:

```bash
DATA_PATH=./14_data/stores/opensearch/content-search \
  OPENSEARCH_INITIAL_ADMIN_PASSWORD=<strong-password> \
  docker compose up -d
docker compose logs -f
docker compose down
```

## Notes

- Security is disabled for local development.
- OpenSearch often needs adequate memory and file descriptor limits.
