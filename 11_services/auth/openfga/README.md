# OpenFGA

## Purpose

Relationship-based authorization and ACL graph service.

## Container

- Image: `openfga/openfga`
- Compose file: `docker-compose.yml`

## Storage

- No durable local storage is configured; the scaffold uses in-memory storage.

## Ports

| Host env var              | Default | Container | Use           |
| ------------------------- | ------: | --------: | ------------- |
| `OPENFGA_HTTP_PORT`       |  `8083` |    `8080` | HTTP API      |
| `OPENFGA_GRPC_PORT`       |  `8081` |    `8081` | gRPC API      |
| `OPENFGA_PLAYGROUND_PORT` |  `3003` |    `3000` | Playground UI |

## Run

```bash
docker compose up -d
docker compose logs -f
docker compose down
```

## Notes

- Uses in-memory storage for local experimentation.
- Add a datastore when moving beyond throwaway tests.
