# Unstructured API

## Purpose

Document partitioning and chunking service for heavier extraction workflows.

## Container

- Image: `downloads.unstructured.io/unstructured-io/unstructured-api:latest`
- Compose file: `docker-compose.yml`

## Storage

- `${DATA_PATH}` -> `/data`: local service data or staging path

Bind to a data instance under `14_data/apps/unstructured/<name>/`.

## Ports

| Host env var | Default | Container | Use |
| --- | ---: | ---: | --- |
| `UNSTRUCTURED_PORT` | `8001` | `8000` | Unstructured API |

## Run

```bash
cmd unstructured ./14_data/apps/unstructured/main
```

Or directly:

```bash
DATA_PATH=./14_data/apps/unstructured/main docker compose up -d
docker compose logs -f
docker compose down
```

## Notes

- Host port defaults to `8001` to avoid the FastAPI scaffold on `8000`.
- This service can be resource heavy.
