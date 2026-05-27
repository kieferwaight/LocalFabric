# MinIO

## Purpose

Object storage for raw files, extracted artifacts, thumbnails, OCR JSON, and
other large binary outputs.

## Container

- Image: `minio/minio`
- Compose file: `docker-compose.yml`

## Storage

- `${DATA_PATH}` -> `/data`: object storage data

Bind to a data instance under `14_data/apps/minio/<name>/`.

## Ports

| Host env var         | Default | Container | Use               |
| -------------------- | ------: | --------: | ----------------- |
| `MINIO_API_PORT`     |  `9000` |    `9000` | S3-compatible API |
| `MINIO_CONSOLE_PORT` |  `9001` |    `9001` | MinIO console     |

## Required Environment

| Var                   | Description   |
| --------------------- | ------------- |
| `MINIO_ROOT_USER`     | Root username |
| `MINIO_ROOT_PASSWORD` | Root password |

## Run

```bash
DATA_PATH=./14_data/apps/minio/main \
  MINIO_ROOT_USER=minio MINIO_ROOT_PASSWORD=<strong-password> \
  docker compose up -d
docker compose logs -f
docker compose down
```

## Notes

- Create buckets from the console or with the MinIO client.
- Credentials must be supplied via environment; no defaults are embedded in compose.
