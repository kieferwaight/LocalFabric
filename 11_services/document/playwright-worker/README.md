# Playwright Browser Worker

## Purpose

Browser automation worker scaffold for URL screenshots and rendered-page
extraction.

## Container

- Image: `contentgraph-playwright-worker:local`
- Build context: `.`
- Compose file: `docker-compose.yml`

## Storage

- `${DATA_PATH}` -> `/work`: local input/output workspace
- Application code lives in `./app`

Bind to a data instance under `14_data/runs/workers/playwright/<name>/`.

## Ports

| Host env var | Default | Container | Use                        |
| ------------ | ------: | --------: | -------------------------- |
| none         |     n/a |       n/a | Worker has no exposed port |

## Run

```bash
DATA_PATH=./14_data/runs/workers/playwright/main docker compose up -d --build
docker compose logs -f
docker compose down
```

## Notes

- Uses the Playwright Python base image with browser dependencies.
- Replace the placeholder loop with browser job handling.
