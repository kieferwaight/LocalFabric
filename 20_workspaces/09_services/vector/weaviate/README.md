# Weaviate

## Purpose

Alternative vector database scaffold for comparison against Qdrant or pgvector.

## Container

- Image: `semitechnologies/weaviate`
- Compose file: `docker-compose.yml`

## Storage

- `${DATA_PATH}` -> `/var/lib/weaviate`: Weaviate persistent data

Bind to a data instance under `14_data/stores/weaviate/<name>/`.

## Ports

| Host env var | Default | Container | Use |
| --- | ---: | ---: | --- |
| `WEAVIATE_HTTP_PORT` | `8085` | `8080` | HTTP API |
| `WEAVIATE_GRPC_PORT` | `50051` | `50051` | gRPC API |

## Run

```bash
cmd weaviate ./14_data/stores/weaviate/research
```

Or directly:

```bash
DATA_PATH=./14_data/stores/weaviate/research docker compose up -d
docker compose logs -f
docker compose down
```

## Notes

- Anonymous access is enabled for local development.
- Defaults to no built-in vectorizer module.
