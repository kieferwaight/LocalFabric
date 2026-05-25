# n8n

## Purpose

Visual workflow automation engine for orchestrating webhooks, scheduled jobs,
and third-party API integrations.

## Container

- Image: `n8nio/n8n:latest`
- Compose file: `docker-compose.yml`

## Storage

- `${DATA_PATH}` -> `/home/node/.n8n`: workflow definitions, credentials,
  execution history, and SQLite state.

Recommended data path: `14_data/apps/n8n/<instance>/` (e.g.
`14_data/apps/n8n/main/`).

## Ports

| Host env var | Default | Container | Use |
| --- | ---: | ---: | --- |
| `N8N_PORT` | `5678` | `5678` | n8n editor and webhook endpoint |

## Optional Environment

| Var | Description |
| --- | --- |
| `N8N_HOST` | Hostname used in webhook URLs (default `localhost`) |
| `GENERIC_TIMEZONE` | Timezone for cron triggers (default `UTC`) |

## Run

```bash
DATA_PATH=$(pwd)/../../../14_data/apps/n8n/main docker compose up -d
docker compose logs -f
docker compose down
```

Or via the service runtime:

```bash
cmd n8n ./14_data/apps/n8n/main
```

## Logs and Runtime State

Container stdout/stderr is captured to `14_data/logs/n8n-<instance>.log`. The
n8n process inside the container writes its own state into the mounted
`${DATA_PATH}`; there is no host-side PID file for the Compose variant.

If running n8n directly on the host (npx, node) instead of via Compose, follow
the host-launched conventions in [SERVICES.md](../../../../SERVICES.md#host-launched-services):

- Log: `14_data/logs/n8n-<instance>.log`
- PID: `14_data/runtime/n8n-<instance>.pid`

## Notes

- Default SQLite backend is fine for local use. For multi-user or production
  setups, configure `DB_TYPE=postgresdb` and point at a Postgres instance.
- Webhook URLs depend on `N8N_HOST` — set it correctly when running behind a
  reverse proxy.
