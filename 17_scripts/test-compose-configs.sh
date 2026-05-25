#!/usr/bin/env bash
set -euo pipefail

# Validate every service docker-compose.yml under 20_workspaces/09_services/.
# Each service lives at <category>/<service>/docker-compose.yml.

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
services_dir="${SERVICES_DIR:-$script_dir/../09_services}"
services_dir="$(cd "$services_dir" && pwd)"

# Compose files require DATA_PATH and some required envs. Provide placeholders
# so `docker compose config` can interpolate without erroring. These are not
# used at runtime, only for syntactic validation.
export DATA_PATH="${DATA_PATH:-/tmp/contentgraph-validate}"
export POSTGRES_USER="${POSTGRES_USER:-validate}"
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-validate}"
export POSTGRES_DB="${POSTGRES_DB:-validate}"
export POSTGRES_SEEDS="${POSTGRES_SEEDS:-validate}"
export NEO4J_PASSWORD="${NEO4J_PASSWORD:-validate}"
export OPENSEARCH_INITIAL_ADMIN_PASSWORD="${OPENSEARCH_INITIAL_ADMIN_PASSWORD:-Validate-Admin-1!}"
export KEYCLOAK_ADMIN="${KEYCLOAK_ADMIN:-validate}"
export KEYCLOAK_ADMIN_PASSWORD="${KEYCLOAK_ADMIN_PASSWORD:-validate}"
export GF_SECURITY_ADMIN_USER="${GF_SECURITY_ADMIN_USER:-validate}"
export GF_SECURITY_ADMIN_PASSWORD="${GF_SECURITY_ADMIN_PASSWORD:-validate}"
export MINIO_ROOT_USER="${MINIO_ROOT_USER:-validate}"
export MINIO_ROOT_PASSWORD="${MINIO_ROOT_PASSWORD:-validate}"
export DATABASE_URL="${DATABASE_URL:-postgresql://validate:validate@pgvector:5432/validate}"

found=0

while IFS= read -r compose_file; do
  found=1
  service_dir="$(dirname "$compose_file")"
  service_name="${service_dir#"$services_dir"/}"

  printf 'checking %s\n' "$service_name"
  (
    cd "$service_dir"
    docker compose config --quiet
  )
done < <(find "$services_dir" -mindepth 3 -maxdepth 3 -name docker-compose.yml -type f | sort)

if [[ "$found" -eq 0 ]]; then
  printf 'no service docker-compose.yml files found under %s\n' "$services_dir" >&2
  exit 1
fi

printf 'all compose configs validated\n'
