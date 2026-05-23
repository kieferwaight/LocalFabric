# GROBID

## Purpose

Optional scientific and scholarly document structure extraction service.

## Container

- Image: `lfoppiano/grobid:0.8.0`
- Compose file: `docker-compose.yml`

## Storage

- `${DATA_PATH}` -> `/opt/grobid/grobid-home/tmp`: temporary GROBID workspace

Bind to a data instance under `14_data/apps/grobid/<name>/`.

## Ports

| Host env var | Default | Container | Use |
| --- | ---: | ---: | --- |
| `GROBID_PORT` | `8070` | `8070` | GROBID HTTP API |

## Run

```bash
cmd grobid ./14_data/apps/grobid/main
```

Or directly:

```bash
DATA_PATH=./14_data/apps/grobid/main docker compose up -d
docker compose logs -f
docker compose down
```

## Notes

- Best used only when paper-like document structure is needed.
- Startup can be slower than lighter extractors.
