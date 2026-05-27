"""Validate every service docker-compose.yml under 11_services/.

Each service lives at `11_services/<category>/<service>/docker-compose.yml`.
We shell out to `docker compose config --quiet` to syntactically validate
each file. Compose interpolation requires several env vars to be present;
we inject placeholders so validation succeeds without real credentials.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SERVICES_DIR = PROJECT_ROOT / "11_services"

# Placeholders for env vars referenced in compose files. Not used at runtime,
# only to let `docker compose config` interpolate without erroring.
PLACEHOLDER_ENV: dict[str, str] = {
    "DATA_PATH": "/tmp/contentgraph-validate",
    "POSTGRES_USER": "validate",
    "POSTGRES_PASSWORD": "validate",
    "POSTGRES_DB": "validate",
    "POSTGRES_SEEDS": "validate",
    "NEO4J_PASSWORD": "validate",
    "OPENSEARCH_INITIAL_ADMIN_PASSWORD": "Validate-Admin-1!",
    "KEYCLOAK_ADMIN": "validate",
    "KEYCLOAK_ADMIN_PASSWORD": "validate",
    "GF_SECURITY_ADMIN_USER": "validate",
    "GF_SECURITY_ADMIN_PASSWORD": "validate",
    "MINIO_ROOT_USER": "validate",
    "MINIO_ROOT_PASSWORD": "validate",
    "DATABASE_URL": "postgresql://validate:validate@pgvector:5432/validate",
}


def _discover_compose_files() -> list[Path]:
    if not SERVICES_DIR.is_dir():
        return []
    return sorted(SERVICES_DIR.glob("*/*/docker-compose.yml"))


def _docker_compose_available() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        result = subprocess.run(
            ["docker", "compose", "version"],
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


COMPOSE_FILES = _discover_compose_files()


def test_service_catalog_is_non_empty():
    assert COMPOSE_FILES, f"no service docker-compose.yml files found under {SERVICES_DIR}"


@pytest.mark.skipif(
    not _docker_compose_available(),
    reason="docker compose CLI not available",
)
@pytest.mark.parametrize(
    "compose_file",
    COMPOSE_FILES,
    ids=[str(p.relative_to(SERVICES_DIR).parent) for p in COMPOSE_FILES],
)
def test_compose_config_is_valid(compose_file: Path):
    env = {**os.environ, **{k: os.environ.get(k, v) for k, v in PLACEHOLDER_ENV.items()}}
    result = subprocess.run(
        ["docker", "compose", "config", "--quiet"],
        cwd=compose_file.parent,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"{compose_file.relative_to(PROJECT_ROOT)} failed `docker compose config`:\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
