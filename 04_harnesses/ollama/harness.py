"""Harness for a local Ollama server. Manages the `ollama serve` process if needed."""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import time
import urllib.error
import urllib.request
from collections.abc import Iterator, Mapping
from typing import Any
from urllib.parse import urljoin

from harnesses.base import Harness, HarnessError, HarnessStatus


class OllamaHarness(Harness):
    """Talks to a local Ollama server, starting it if it is not already running.

    Config keys:
        base_url:      Default ``http://localhost:11434``.
        model:         Default ``llama3.2``.
        timeout:       HTTP timeout seconds (default 120).
        manage_server: If True (default), ``start`` will launch ``ollama serve``
                       when the server is not already reachable. Otherwise it
                       assumes the user runs the server.
        startup_wait:  Max seconds to wait for the server to come up (default 15).
    """

    name = "ollama"
    DEFAULT_BASE_URL = "http://localhost:11434"

    def __init__(self, config: Mapping[str, Any] | None = None) -> None:
        super().__init__(config)
        self.base_url: str = self.config.get("base_url", self.DEFAULT_BASE_URL).rstrip("/")
        self.model: str = self.config.get("model", "llama3.2")
        self.timeout: float = float(self.config.get("timeout", 120))
        self.manage_server: bool = bool(self.config.get("manage_server", True))
        self.startup_wait: float = float(self.config.get("startup_wait", 15))
        self._proc: subprocess.Popen[bytes] | None = None

    # ----------------------------------------------------------------- internals
    def _url(self, path: str) -> str:
        return urljoin(self.base_url + "/", path.lstrip("/"))

    def _http(
        self,
        path: str,
        method: str = "GET",
        body: Mapping[str, Any] | None = None,
        timeout: float | None = None,
        stream: bool = False,
    ) -> Any:
        data = None
        headers = {"Content-Type": "application/json"} if body is not None else {}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(self._url(path), data=data, headers=headers, method=method)
        return urllib.request.urlopen(req, timeout=timeout or self.timeout)

    def _server_reachable(self) -> bool:
        try:
            with self._http("/", timeout=2):
                return True
        except (urllib.error.URLError, OSError):
            return False

    def _spawn_server(self) -> None:
        if shutil.which("ollama") is None:
            raise HarnessError("`ollama` binary not on PATH; install or start it manually")
        env = os.environ.copy()
        env.setdefault("OLLAMA_HOST", self.base_url.replace("http://", ""))
        self._proc = subprocess.Popen(
            ["ollama", "serve"],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        self._record(f"spawned ollama serve pid={self._proc.pid}")

        deadline = time.monotonic() + self.startup_wait
        while time.monotonic() < deadline:
            if self._server_reachable():
                return
            time.sleep(0.5)
        raise HarnessError(f"ollama did not become reachable within {self.startup_wait}s")

    # ----------------------------------------------------------------- lifecycle
    def start(self) -> HarnessStatus:
        if self._server_reachable():
            return self._set_state("running", f"already up @ {self.base_url}")
        if not self.manage_server:
            return self._set_state("error", f"not reachable @ {self.base_url}")
        self._spawn_server()
        return self._set_state(
            "running", f"spawned ollama serve pid={self._proc.pid if self._proc else '?'}"
        )

    def stop(self) -> HarnessStatus:
        if self._proc is not None:
            try:
                os.killpg(os.getpgid(self._proc.pid), signal.SIGTERM)
                self._proc.wait(timeout=5)
            except (ProcessLookupError, subprocess.TimeoutExpired) as exc:
                self._record(f"stop warning: {exc}")
            finally:
                self._proc = None
        return self._set_state("stopped")

    def status(self) -> HarnessStatus:
        try:
            with self._http("/api/tags", timeout=2) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            models = [m.get("name") for m in payload.get("models", [])]
            return HarnessStatus(
                name=self.name,
                state="running",
                detail=f"{len(models)} model(s) available",
                metadata={"models": models, "base_url": self.base_url},
            )
        except Exception as exc:  # noqa: BLE001
            return HarnessStatus(name=self.name, state="stopped", detail=str(exc))

    # ------------------------------------------------------------------ requests
    def invoke(self, request: Mapping[str, Any]) -> dict[str, Any]:
        body = {
            "model": request.get("model", self.model),
            "messages": request.get("messages")
            or [{"role": "user", "content": request.get("prompt", "")}],
            "stream": False,
        }
        if "options" in request:
            body["options"] = request["options"]
        try:
            with self._http("/api/chat", method="POST", body=body) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            self._record(f"invoke error: {exc}")
            raise HarnessError(f"ollama invoke failed: {exc}") from exc
        self._record(f"invoke ok model={body['model']}")
        return payload

    def embed(self, text: str, model: str | None = None) -> list[float]:
        """Generate one embedding vector through the Ollama API."""
        body = {"model": model or self.model, "prompt": text}
        try:
            with self._http("/api/embeddings", method="POST", body=body) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            self._record(f"embed error: {exc}")
            raise HarnessError(f"ollama embed failed: {exc}") from exc
        self._record(f"embed ok model={body['model']}")
        return list(payload.get("embedding", []))

    def stream(self, request: Mapping[str, Any]) -> Iterator[dict[str, Any]]:
        body = {
            "model": request.get("model", self.model),
            "messages": request.get("messages")
            or [{"role": "user", "content": request.get("prompt", "")}],
            "stream": True,
        }
        if "options" in request:
            body["options"] = request["options"]
        try:
            with self._http("/api/chat", method="POST", body=body) as resp:
                for raw in resp:
                    line = raw.decode("utf-8").strip()
                    if not line:
                        continue
                    yield json.loads(line)
            self._record(f"stream ok model={body['model']}")
        except Exception as exc:  # noqa: BLE001
            self._record(f"stream error: {exc}")
            raise HarnessError(f"ollama stream failed: {exc}") from exc

    # ---------------------------------------------------------------- observers
    def logs(self, tail: int = 50) -> list[str]:
        return list(self._logs)[-tail:]

    def health(self) -> HarnessStatus:
        try:
            with self._http("/", timeout=2) as resp:
                resp.read()
            return HarnessStatus(name=self.name, state="ready", detail="ollama reachable")
        except Exception as exc:  # noqa: BLE001
            return HarnessStatus(name=self.name, state="error", detail=str(exc))
