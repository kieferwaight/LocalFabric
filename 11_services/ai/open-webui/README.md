# Open WebUI

## Purpose

Optional UI for testing local models, usually against Ollama.

## Container

- Image: `ghcr.io/open-webui/open-webui:main`
- Compose file: `docker-compose.yml`

## Storage

- `${DATA_PATH}` -> `/app/backend/data`: Open WebUI backend data

Bind to a data instance under `14_data/apps/openwebui/<name>/`.

## Ports

| Host env var      | Default | Container | Use    |
| ----------------- | ------: | --------: | ------ |
| `OPEN_WEBUI_PORT` |  `3001` |    `8080` | Web UI |

## Run

```bash
cmd openwebui ./14_data/apps/openwebui/main
```

Or directly:

```bash
DATA_PATH=./14_data/apps/openwebui/main docker compose up -d
docker compose logs -f
docker compose down
```

## Notes

- Expects Ollama at `http://ollama:11434` when attached to a shared network.
- Override `OLLAMA_BASE_URL` for standalone use.
