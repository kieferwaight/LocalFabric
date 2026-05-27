"""Harness for an LM Studio local server — OpenAI-compatible HTTP endpoint."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from collections import deque
from collections.abc import Iterator, Mapping
from typing import Any

from harnesses.base import Harness, HarnessError, HarnessStatus


class LMStudioHarness(Harness):
    """Talks to an LM Studio local server using the `openai` SDK.

    LM Studio exposes an OpenAI-compatible API, by default at
    ``http://localhost:1234/v1``. With ``manage_server=True`` (the default),
    ``start`` will run ``lms server start`` if the server isn't already up;
    otherwise ``start`` only initialises the SDK client. ``status`` and
    ``health`` perform a reachability check against ``/models``.

    Config keys:
        base_url:      Default ``http://localhost:1234/v1``.
        api_key:       Default ``lm-studio`` (LM Studio ignores it but the SDK
                       requires *some* value). Falls back to ``LMSTUDIO_API_KEY``.
        model:         Loaded model id (default ``local-model``).
        timeout:       Default 120s (local models can be slow on first load).
        manage_server: If True (default), ``start`` runs ``lms server start``
                       when the server is unreachable.
        startup_wait:  Max seconds to wait for the server to come up (default 20).
    """

    name = "lmstudio"
    DEFAULT_BASE_URL = "http://localhost:1234/v1"

    def __init__(self, config: Mapping[str, Any] | None = None) -> None:
        super().__init__(config)
        self._client: Any | None = None
        self._request_ids: deque[str] = deque(maxlen=64)
        self.base_url: str = self.config.get("base_url", self.DEFAULT_BASE_URL)
        self.api_key: str = (
            self.config.get("api_key") or os.environ.get("LMSTUDIO_API_KEY") or "lm-studio"
        )
        self.model: str = self.config.get("model", "local-model")
        self.timeout: float = float(self.config.get("timeout", 120))
        self.manage_server: bool = bool(self.config.get("manage_server", True))
        self.startup_wait: float = float(self.config.get("startup_wait", 20))

    # ----------------------------------------------------------------- internals
    def _ensure_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            from openai import OpenAI  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise HarnessError(
                "openai SDK is not installed — run `uv sync --extra llm` "
                "to enable the LM Studio / OpenAI / Anthropic providers."
            ) from exc
        self._client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
        )
        return self._client

    def _build_chat_kwargs(self, request: Mapping[str, Any]) -> dict[str, Any]:
        messages = request.get("messages")
        if messages is None:
            messages = [{"role": "user", "content": request.get("prompt", "")}]
        kwargs: dict[str, Any] = {
            "model": request.get("model", self.model),
            "messages": list(messages),
        }
        for key in ("temperature", "top_p", "max_tokens", "stop"):
            if key in request:
                kwargs[key] = request[key]
        return kwargs

    def _server_reachable(self) -> bool:
        # Use plain urllib rather than the openai SDK so the probe still works
        # when the SDK isn't installed (the server's reachability is independent
        # of the client library).
        probe_url = self.base_url.rstrip("/") + "/models"
        try:
            with urllib.request.urlopen(probe_url, timeout=2) as resp:
                return 200 <= resp.status < 500
        except (urllib.error.URLError, OSError):
            return False

    def _spawn_server(self) -> None:
        if shutil.which("lms") is None:
            raise HarnessError("`lms` binary not on PATH; install LM Studio or start it manually")
        try:
            subprocess.run(
                ["lms", "server", "start"],
                check=True,
                capture_output=True,
                text=True,
                timeout=self.startup_wait,
            )
        except subprocess.CalledProcessError as exc:
            detail = exc.stderr.strip() or exc.stdout.strip()
            raise HarnessError(
                f"`lms server start` failed (exit {exc.returncode}): {detail}"
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise HarnessError(f"`lms server start` timed out after {self.startup_wait}s") from exc
        self._record("ran `lms server start`")

        deadline = time.monotonic() + self.startup_wait
        # Reset the SDK client so the post-spawn probe doesn't reuse a stale
        # connection from before the server came up.
        self._client = None
        while time.monotonic() < deadline:
            if self._server_reachable():
                return
            time.sleep(0.5)
        raise HarnessError(f"lmstudio did not become reachable within {self.startup_wait}s")

    # ----------------------------------------------------------------- lifecycle
    def start(self) -> HarnessStatus:
        if self._server_reachable():
            return self._set_state("running", f"already up @ {self.base_url}")
        if not self.manage_server:
            self._ensure_client()
            return self._set_state("error", f"not reachable @ {self.base_url}")
        self._spawn_server()
        return self._set_state("running", f"started lms server @ {self.base_url}")

    def stop(self) -> HarnessStatus:
        self._client = None
        return self._set_state("stopped")

    def status(self) -> HarnessStatus:
        return HarnessStatus(
            name=self.name,
            state=self._state,
            detail=f"base_url={self.base_url} model={self.model}",
            metadata={
                "base_url": self.base_url,
                "model": self.model,
                "request_ids": list(self._request_ids),
            },
        )

    # ------------------------------------------------------------------ requests
    def invoke(self, request: Mapping[str, Any]) -> dict[str, Any]:
        client = self._ensure_client()
        kwargs = self._build_chat_kwargs(request)
        try:
            response = client.chat.completions.create(**kwargs)
        except Exception as exc:  # noqa: BLE001
            self._record(f"invoke error: {exc}")
            raise HarnessError(f"lmstudio invoke failed: {exc}") from exc

        rid = getattr(response, "id", "") or ""
        if rid:
            self._request_ids.append(rid)
        self._record(f"invoke ok id={rid}")
        return {
            "id": rid,
            "model": getattr(response, "model", self.model),
            "choices": [c.model_dump() for c in getattr(response, "choices", [])],
            "usage": getattr(getattr(response, "usage", None), "model_dump", lambda: {})(),
        }

    def stream(self, request: Mapping[str, Any]) -> Iterator[dict[str, Any]]:
        client = self._ensure_client()
        kwargs = self._build_chat_kwargs(request)
        kwargs["stream"] = True
        try:
            for chunk in client.chat.completions.create(**kwargs):
                yield chunk.model_dump() if hasattr(chunk, "model_dump") else dict(chunk)
            self._record("stream ok")
        except Exception as exc:  # noqa: BLE001
            self._record(f"stream error: {exc}")
            raise HarnessError(f"lmstudio stream failed: {exc}") from exc

    # ---------------------------------------------------------------- observers
    def logs(self, tail: int = 50) -> list[str]:
        return list(self._logs)[-tail:]

    def health(self) -> HarnessStatus:
        try:
            client = self._ensure_client()
            client.models.list()
            return HarnessStatus(name=self.name, state="ready", detail="lmstudio reachable")
        except Exception as exc:  # noqa: BLE001
            return HarnessStatus(name=self.name, state="error", detail=str(exc))
