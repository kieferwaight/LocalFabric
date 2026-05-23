# Gitea

## Purpose

Optional local git server mirror and classification target.

## Container

- Image: `gitea/gitea:latest`
- Compose file: `docker-compose.yml`

## Storage

- `${DATA_PATH}` -> `/data`: Gitea repositories, database, and config

Bind to a data instance under `14_data/apps/gitea/<name>/`.

## Ports

| Host env var | Default | Container | Use |
| --- | ---: | ---: | --- |
| `GITEA_HTTP_PORT` | `3000` | `3000` | Web UI |
| `GITEA_SSH_PORT` | `2222` | `22` | SSH git access |

## Run

```bash
DATA_PATH=./14_data/apps/gitea/main docker compose up -d
docker compose logs -f
docker compose down
```

## Notes

- Defaults to SQLite for a self-contained local setup.
- Change the UID/GID values via `USER_UID`/`USER_GID` if file ownership does not match your user.
