# Service Name

## Purpose

One or two sentences describing why this service exists in the system.

## Container

- Image: `image/name:tag` or `local-build-name:local`
- Compose file: `docker-compose.yml`
- Build context: `.` when this service uses a local Dockerfile

## Storage

- `${DATA_PATH}` -> `/path/in/container`: durable service data, when applicable
- `./config`: local configuration mounted read-only, when applicable

Bind to a data instance under `14_data/<category>/<service>/<name>/`.

## Ports

| Host env var   | Default | Container | Use           |
| -------------- | ------: | --------: | ------------- |
| `SERVICE_PORT` |  `0000` |    `0000` | Main endpoint |

## Required Environment

| Var              | Description             |
| ---------------- | ----------------------- |
| `EXAMPLE_SECRET` | What this secret is for |

Omit this section when the service has no required environment variables.

## Run

```bash
cmd <service> ./14_data/<category>/<service>/<name>
```

Or directly:

```bash
DATA_PATH=./14_data/<category>/<service>/<name> docker compose up -d
docker compose logs -f
docker compose down
```

## Notes

- All persistent state must map to `${DATA_PATH}`.
- Host ports must be parameterized as `${PORT_VAR:-default}:container-port`.
- Secrets must be sourced from the environment; do not embed defaults.
- Document integrations with other services here rather than wiring them into a
  shared compose file.
