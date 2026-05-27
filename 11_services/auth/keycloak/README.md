# Keycloak

## Purpose

Auth and SSO service for local enterprise identity experiments.

## Container

- Image: `quay.io/keycloak/keycloak`
- Compose file: `docker-compose.yml`

## Storage

- `${DATA_PATH}` -> `/opt/keycloak/data`: Keycloak local data

Bind to a data instance under `14_data/apps/keycloak/<name>/`.

## Ports

| Host env var    | Default | Container | Use             |
| --------------- | ------: | --------: | --------------- |
| `KEYCLOAK_PORT` |  `8082` |    `8080` | Keycloak UI/API |

## Required Environment

| Var                       | Description            |
| ------------------------- | ---------------------- |
| `KEYCLOAK_ADMIN`          | Initial admin username |
| `KEYCLOAK_ADMIN_PASSWORD` | Initial admin password |

## Run

```bash
cmd keycloak ./14_data/apps/keycloak/main
```

Or directly:

```bash
DATA_PATH=./14_data/apps/keycloak/main \
  KEYCLOAK_ADMIN=admin KEYCLOAK_ADMIN_PASSWORD=<strong-password> \
  docker compose up -d
docker compose logs -f
docker compose down
```

## Notes

- Runs with `start-dev`.
- Credentials must be supplied via environment; no defaults are embedded in compose.
