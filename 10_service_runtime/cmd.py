"""Command entry point for binding catalog services to persistent data paths.

The service runtime owns service lookup and data-path binding. Docker process
lifecycle is delegated to ``DockerServiceHarness`` in the harness layer.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from harnesses.docker_service import DockerServiceHarness


_WORKSPACES_ROOT = Path(__file__).resolve().parent.parent
_SERVICES_DIR = _WORKSPACES_ROOT / "09_services"
_REGISTRY = _WORKSPACES_ROOT / "14_data" / "_registry" / "services.yaml"


def _load_registry() -> dict:
    with _REGISTRY.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _resolve_service_dir(service: str, registry: dict) -> Path:
    entry = registry.get("services", {}).get(service)
    if entry is None:
        raise SystemExit(f"cmd: unknown service '{service}' (not in services.yaml)")
    path = _SERVICES_DIR / entry["category"] / service
    if not path.is_dir():
        raise SystemExit(f"cmd: service dir not found: {path}")
    return path


def _harness(service: str, service_dir: Path, data_path: Path) -> DockerServiceHarness:
    data_path.mkdir(parents=True, exist_ok=True)
    return DockerServiceHarness(
        {
            "compose_file": service_dir / "docker-compose.yml",
            "project_name": f"{service}-{data_path.name}",
            "env": {"DATA_PATH": str(data_path.resolve())},
        }
    )


def _run_action(action: str, service: str, service_dir: Path, data_path: Path) -> int:
    harness = _harness(service, service_dir, data_path)
    if action == "up":
        status = harness.start()
    elif action == "down":
        status = harness.stop()
    else:
        status = harness.status()
    print(status.detail)
    return 0 if status.ok() or (action == "down" and status.state == "stopped") else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cmd", description="Service runtime entry point.")
    parser.add_argument("action", choices=("down", "status", "up"), nargs="?", default="up")
    parser.add_argument("service")
    parser.add_argument("data_path", type=Path)
    args = parser.parse_args(argv)

    service_dir = _resolve_service_dir(args.service, _load_registry())
    return _run_action(args.action, args.service, service_dir, args.data_path)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
