# Qdrant

## Purpose

Vector database for similarity search when pgvector is not enough.

## Container

- Image: `qdrant/qdrant`
- Compose file: `docker-compose.yml`

## Storage

- `${DATA_PATH}` -> `/qdrant/storage`: Qdrant vector storage

Bind to a data instance under `14_data/stores/qdrant/<name>/`.

## Ports

| Host env var | Default | Container | Use |
| --- | ---: | ---: | --- |
| `QDRANT_HTTP_PORT` | `6333` | `6333` | HTTP API |
| `QDRANT_GRPC_PORT` | `6334` | `6334` | gRPC API |

## Run

```bash
cmd qdrant ./14_data/stores/qdrant/codebase
```

Or directly:

```bash
DATA_PATH=./14_data/stores/qdrant/codebase docker compose up -d
docker compose logs -f
docker compose down
```

## Notes

- Use alongside pgvector only when comparing vector backends or scaling needs.
