# LibreOffice Headless

## Purpose

Office conversion worker scaffold for document conversion fallback workflows.

## Container

- Image: `contentgraph-libreoffice:local`
- Build context: `.`
- Compose file: `docker-compose.yml`

## Storage

- `${DATA_PATH}` -> `/work`: local input/output workspace
- Application code lives in `./app`

Bind to a data instance under `14_data/runs/workers/libreoffice/<name>/`.

## Ports

| Host env var | Default | Container | Use                        |
| ------------ | ------: | --------: | -------------------------- |
| none         |     n/a |       n/a | Worker has no exposed port |

## Run

```bash
DATA_PATH=./14_data/runs/workers/libreoffice/main docker compose up -d --build
docker compose logs -f
docker compose down
```

## Notes

- Installs LibreOffice into a slim Python image.
- Replace the placeholder loop with conversion job handling.
