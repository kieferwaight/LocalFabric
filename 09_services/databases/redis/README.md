# Redis

## Purpose

Cache, queue, rate-limit, and ephemeral job state service for local development.

## Container

- Image: `redis:7`
- Compose file: `docker-compose.yml`

## Storage

- `${DATA_PATH}` -> `/data`: append-only Redis persistence

Bind to a data instance under `14_data/stores/redis/<name>/`.

## Ports

| Host env var | Default | Container | Use                  |
| ------------ | ------: | --------: | -------------------- |
| `REDIS_PORT` |  `6379` |    `6379` | Redis client traffic |

## Run

```bash
cmd redis ./14_data/stores/redis/cache-main
```

Or directly:

```bash
DATA_PATH=./14_data/stores/redis/cache-main docker compose up -d
docker compose logs -f
docker compose down
```

## Notes

- Append-only persistence is enabled.
- No password is set by default.
