# Apache Tika

## Purpose

MIME detection, text extraction, and document metadata extraction service.

## Container

- Image: `apache/tika:latest-full`
- Compose file: `docker-compose.yml`

## Storage

- No durable local storage is configured.

## Ports

| Host env var | Default | Container | Use |
| --- | ---: | ---: | --- |
| `TIKA_PORT` | `9998` | `9998` | Tika HTTP API |

## Run

```bash
docker compose up -d
docker compose logs -f
docker compose down
```

## Notes

- Use `latest-full` for broad parser coverage.
- Consider pinning the image digest for production-like tests.
