# Jaeger

## Purpose

Distributed tracing collector and UI for ingestion pipeline traces.

## Container

- Image: `jaegertracing/all-in-one`
- Compose file: `docker-compose.yml`

## Storage

- `${DATA_PATH}` -> `/tmp`: local temporary Jaeger data path

Bind to a data instance under `14_data/apps/jaeger/<name>/`.

## Ports

| Host env var            | Default | Container | Use       |
| ----------------------- | ------: | --------: | --------- |
| `JAEGER_UI_PORT`        | `16686` |   `16686` | Jaeger UI |
| `JAEGER_OTLP_GRPC_PORT` |  `4317` |    `4317` | OTLP gRPC |
| `JAEGER_OTLP_HTTP_PORT` |  `4318` |    `4318` | OTLP HTTP |

## Run

```bash
cmd jaeger ./14_data/apps/jaeger/main
```

Or directly:

```bash
DATA_PATH=./14_data/apps/jaeger/main docker compose up -d
docker compose logs -f
docker compose down
```

## Notes

- OTLP collection is enabled.
