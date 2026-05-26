# Temporal UI

## Purpose

Optional web UI for inspecting Temporal workflows, histories, and task queues.

## Container

- Image: `temporalio/ui`
- Compose file: `docker-compose.yml`

## Storage

- No durable local storage is configured.

## Ports

| Host env var       | Default | Container | Use         |
| ------------------ | ------: | --------: | ----------- |
| `TEMPORAL_UI_PORT` |  `8084` |    `8080` | Temporal UI |

## Run

```bash
docker compose up -d
docker compose logs -f
docker compose down
```

## Notes

- Expects Temporal at `temporal:7233` when attached to a shared network.
- Override `TEMPORAL_ADDRESS` for standalone use.
