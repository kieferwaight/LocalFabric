# ClamAV

## Purpose

Antivirus scanning service for uploads before extraction or indexing.

## Container

- Image: `clamav/clamav`
- Compose file: `docker-compose.yml`

## Storage

- `${DATA_PATH}` -> `/var/lib/clamav`: ClamAV signature database

Bind to a data instance under `14_data/apps/clamav/<name>/`.

## Ports

| Host env var | Default | Container | Use |
| --- | ---: | ---: | --- |
| `CLAMAV_PORT` | `3310` | `3310` | clamd TCP service |

## Run

```bash
cmd clamav ./14_data/apps/clamav/main
```

Or directly:

```bash
DATA_PATH=./14_data/apps/clamav/main docker compose up -d
docker compose logs -f
docker compose down
```

## Notes

- Initial signature download can take time.
- Keep signatures updated for meaningful scans.
