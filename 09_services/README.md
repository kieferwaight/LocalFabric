# Service Catalog

Each folder under this directory is a self-contained Docker Compose scaffold for
a single service. Services are grouped by category. There is no root Compose
orchestrator; start services from their own folders via the service runtime
(`10_service_runtime/`) or directly with `docker compose`.

See [SERVICES.md](../../SERVICES.md) for the service contract: every service
binds persistent state to `${DATA_PATH}`, parameterizes its host ports, and
sources secrets from the environment (no defaults embedded in compose files).

## Standard README Template

Every service README follows the same sections:

1. Purpose
2. Container
3. Storage
4. Ports
5. Required Environment (when applicable)
6. Run
7. Notes

The reusable template is in [README_TEMPLATE.md](README_TEMPLATE.md).

## Categories

| Category | Description |
| --- | --- |
| `ai/` | Local LLM runtimes and chat UIs |
| `databases/` | Relational/key-value stores |
| `vector/` | Vector databases |
| `search/` | Full-text search + dashboards |
| `graph/` | Graph databases |
| `auth/` | Identity, authorization, and policy services |
| `observability/` | Metrics, traces, dashboards |
| `document/` | Document extraction, OCR, conversion, scanning |
| `workers/` | Background workers and durable workflow engines |
| `dev/` | Optional developer tooling (notebooks, git server) |
| `proxy/` | Reverse proxies / edge routing |
| `storage/` | Object storage |

## Service Lookup

| Service | Folder | Category | Image/build | Ports |
| --- | --- | --- | --- | --- |
| Ollama | [ai/ollama](ai/ollama/README.md) | ai | `ollama/ollama` | `11434` |
| Open WebUI | [ai/open-webui](ai/open-webui/README.md) | ai | `ghcr.io/open-webui/open-webui:main` | `3001 -> 8080` |
| PostgreSQL | [databases/postgres](databases/postgres/README.md) | databases | `postgres:16` | `5433 -> 5432` |
| pgvector | [databases/pgvector](databases/pgvector/README.md) | databases | `pgvector/pgvector:pg16` | `5432` |
| Redis | [databases/redis](databases/redis/README.md) | databases | `redis:7` | `6379` |
| Qdrant | [vector/qdrant](vector/qdrant/README.md) | vector | `qdrant/qdrant` | `6333`, `6334` |
| Weaviate | [vector/weaviate](vector/weaviate/README.md) | vector | `semitechnologies/weaviate` | `8085 -> 8080`, `50051` |
| OpenSearch | [search/opensearch](search/opensearch/README.md) | search | `opensearchproject/opensearch:2` | `9200`, `9600` |
| OpenSearch Dashboards | [search/opensearch-dashboards](search/opensearch-dashboards/README.md) | search | `opensearchproject/opensearch-dashboards:2` | `5601` |
| Neo4j | [graph/neo4j](graph/neo4j/README.md) | graph | `neo4j:5` | `7474`, `7687` |
| Keycloak | [auth/keycloak](auth/keycloak/README.md) | auth | `quay.io/keycloak/keycloak` | `8082 -> 8080` |
| OpenFGA | [auth/openfga](auth/openfga/README.md) | auth | `openfga/openfga` | `8083 -> 8080`, `8081`, `3003 -> 3000` |
| Casbin service | [auth/casbin-service](auth/casbin-service/README.md) | auth | local build | `8090 -> 8080` |
| Prometheus | [observability/prometheus](observability/prometheus/README.md) | observability | `prom/prometheus` | `9090` |
| Grafana | [observability/grafana](observability/grafana/README.md) | observability | `grafana/grafana` | `3002 -> 3000` |
| Jaeger | [observability/jaeger](observability/jaeger/README.md) | observability | `jaegertracing/all-in-one` | `16686`, `4317`, `4318` |
| Apache Tika | [document/tika](document/tika/README.md) | document | `apache/tika:latest-full` | `9998` |
| GROBID | [document/grobid](document/grobid/README.md) | document | `lfoppiano/grobid:0.8.0` | `8070` |
| Unstructured API | [document/unstructured](document/unstructured/README.md) | document | `downloads.unstructured.io/unstructured-io/unstructured-api:latest` | `8001 -> 8000` |
| Tesseract OCR | [document/tesseract-ocr](document/tesseract-ocr/README.md) | document | local build | none |
| LibreOffice headless | [document/libreoffice](document/libreoffice/README.md) | document | local build | none |
| ClamAV | [document/clamav](document/clamav/README.md) | document | `clamav/clamav` | `3310` |
| Playwright worker | [document/playwright-worker](document/playwright-worker/README.md) | document | local build | none |
| Temporal | [workers/temporal](workers/temporal/README.md) | workers | `temporalio/auto-setup` | `7233` |
| Temporal UI | [workers/temporal-ui](workers/temporal-ui/README.md) | workers | `temporalio/ui` | `8084 -> 8080` |
| Worker service | [workers/worker](workers/worker/README.md) | workers | local build | none |
| FastAPI app | [workers/fastapi](workers/fastapi/README.md) | workers | local build | `8000` |
| Jupyter notebook | [dev/jupyter](dev/jupyter/README.md) | dev | `jupyter/base-notebook` | `8888` |
| Gitea | [dev/gitea](dev/gitea/README.md) | dev | `gitea/gitea:latest` | `3000`, `2222 -> 22` |
| Traefik | [proxy/traefik](proxy/traefik/README.md) | proxy | `traefik:v3` | `80`, `443`, `8080` |
| MinIO | [storage/minio](storage/minio/README.md) | storage | `minio/minio` | `9000`, `9001` |

## Starting A Service

Each service expects `DATA_PATH` (and any required credentials) to be provided
via the environment. Compose files do not embed defaults for paths or secrets.

```bash
cd 20_workspaces/09_services/databases/pgvector
DATA_PATH=../../../14_data/stores/pgvector/research \
  POSTGRES_USER=postgres POSTGRES_PASSWORD=postgres POSTGRES_DB=contentgraph \
  docker compose up -d
```

Or use the service runtime:

```bash
cmd pgvector ./14_data/stores/pgvector/research
```

Use each service README for credentials, storage paths, and port override
variables.
