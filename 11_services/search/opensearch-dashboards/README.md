# OpenSearch Dashboards

## Purpose

Optional admin and exploration UI for OpenSearch indexes.

## Container

- Image: `opensearchproject/opensearch-dashboards:2`
- Compose file: `docker-compose.yml`

## Storage

- No durable local storage is configured.

## Ports

| Host env var                 | Default | Container | Use           |
| ---------------------------- | ------: | --------: | ------------- |
| `OPENSEARCH_DASHBOARDS_PORT` |  `5601` |    `5601` | Dashboards UI |

## Run

```bash
docker compose up -d
docker compose logs -f
docker compose down
```

## Notes

- Expects OpenSearch at `http://opensearch:9200` when attached to a shared network.
- Override `OPENSEARCH_HOSTS` for standalone use.
