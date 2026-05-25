"""Generic harness for a Docker Compose-backed service from the service catalog."""

from __future__ import annotations

import os
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterator, List, Mapping, Optional, Sequence

from harnesses.base import Harness, HarnessError, HarnessStatus


class DockerServiceHarness(Harness):
    """Drives a Docker Compose service via the `docker compose` CLI.

    Services in the repo's ``09_services/`` catalog define their own
    ``compose.yaml``. This harness wraps the lifecycle for any one of them:

    * ``start``  -> ``docker compose -f <compose> up -d``
    * ``stop``   -> ``docker compose -f <compose> down``
    * ``status`` -> ``docker compose -f <compose> ps --format json``
    * ``logs``   -> ``docker compose -f <compose> logs --tail <n>``
    * ``health`` -> HTTP GET against ``health_url`` (if configured)
    * ``invoke`` and ``stream`` are not meaningful — services are consumed via
      drivers / adapters — and raise ``HarnessError``.

    Config keys:
        compose_file:  Path to ``compose.yaml`` (required).
        project_name:  Compose project name (default: parent dir of compose file).
        service:       Optional specific service within the compose file.
        health_url:    HTTP URL to probe for ``health()``.
        env_file:      Optional path to a .env file passed via ``--env-file``.
        env:           Optional dict of extra env vars for the docker CLI.
    """

    name = "docker_service"

    def __init__(self, config: Optional[Mapping[str, Any]] = None) -> None:
        super().__init__(config)
        compose_file = self.config.get("compose_file")
        if not compose_file:
            raise HarnessError("docker_service harness requires `compose_file`")
        self.compose_file: Path = Path(compose_file).expanduser().resolve()
        if not self.compose_file.exists():
            raise HarnessError(f"compose file not found: {self.compose_file}")

        self.project_name: str = self.config.get("project_name") or self.compose_file.parent.name
        self.service: Optional[str] = self.config.get("service")
        self.health_url: Optional[str] = self.config.get("health_url")
        self.env_file: Optional[str] = self.config.get("env_file")
        self._extra_env: Dict[str, str] = dict(self.config.get("env", {}))

        if shutil.which("docker") is None:
            raise HarnessError("`docker` CLI is not on PATH")

        # Override harness name with the service identifier for nicer logging.
        self.name = f"docker:{self.project_name}" + (f":{self.service}" if self.service else "")

    # ----------------------------------------------------------------- internals
    def _compose_cmd(self, *args: str) -> List[str]:
        cmd: List[str] = ["docker", "compose", "-f", str(self.compose_file), "-p", self.project_name]
        if self.env_file:
            cmd += ["--env-file", self.env_file]
        cmd += list(args)
        if self.service and args and args[0] in {"logs", "ps", "restart", "stop", "start"}:
            cmd.append(self.service)
        return cmd

    def _run(self, args: Sequence[str], check: bool = True, capture: bool = True) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.update(self._extra_env)
        self._record(f"$ {' '.join(args)}")
        return subprocess.run(
            list(args),
            check=check,
            env=env,
            text=True,
            capture_output=capture,
        )

    # ----------------------------------------------------------------- lifecycle
    def start(self) -> HarnessStatus:
        try:
            self._run(self._compose_cmd("up", "-d"))
        except subprocess.CalledProcessError as exc:
            self._record(f"start failed: {exc.stderr}")
            return self._set_state("error", exc.stderr or str(exc))
        return self._set_state("running", "compose up -d ok")

    def stop(self) -> HarnessStatus:
        try:
            self._run(self._compose_cmd("down"))
        except subprocess.CalledProcessError as exc:
            self._record(f"stop failed: {exc.stderr}")
            return self._set_state("error", exc.stderr or str(exc))
        return self._set_state("stopped", "compose down ok")

    def status(self) -> HarnessStatus:
        try:
            result = self._run(self._compose_cmd("ps", "--format", "json"), check=False)
        except FileNotFoundError as exc:
            return HarnessStatus(name=self.name, state="error", detail=str(exc))

        running = (result.stdout or "").strip()
        if result.returncode != 0:
            return HarnessStatus(
                name=self.name, state="error", detail=(result.stderr or "").strip()
            )
        return HarnessStatus(
            name=self.name,
            state="running" if running else "stopped",
            detail=f"{len(running.splitlines())} container line(s)",
            metadata={"compose_file": str(self.compose_file), "raw": running},
        )

    # --------------------------------------------------------------- not-invokable
    def invoke(self, request: Mapping[str, Any]) -> Dict[str, Any]:
        raise HarnessError(
            "docker_service is not directly invokable — consume it via a driver or adapter"
        )

    def stream(self, request: Mapping[str, Any]) -> Iterator[Dict[str, Any]]:
        raise HarnessError(
            "docker_service does not support stream() — use a driver/adapter"
        )

    # ---------------------------------------------------------------- observers
    def logs(self, tail: int = 50) -> list[str]:
        try:
            result = self._run(
                self._compose_cmd("logs", "--no-color", "--tail", str(tail)),
                check=False,
            )
        except FileNotFoundError:
            return list(self._logs)[-tail:]
        out = (result.stdout or "").splitlines()
        return out[-tail:] if out else list(self._logs)[-tail:]

    def health(self) -> HarnessStatus:
        if not self.health_url:
            # Fall back to ps-derived liveness.
            return self.status()
        try:
            with urllib.request.urlopen(self.health_url, timeout=5) as resp:
                code = resp.getcode()
            if 200 <= code < 400:
                return HarnessStatus(
                    name=self.name, state="ready", detail=f"GET {self.health_url} -> {code}"
                )
            return HarnessStatus(
                name=self.name, state="degraded", detail=f"GET {self.health_url} -> {code}"
            )
        except (urllib.error.URLError, OSError) as exc:
            return HarnessStatus(name=self.name, state="error", detail=str(exc))
