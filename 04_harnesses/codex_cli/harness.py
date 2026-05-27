"""Harness for the locally installed ``codex`` CLI.

Parallel transport channel to ``harnesses.codex.CodexHarness`` (SDK).
Routes prompts through the user's installed ``codex`` binary via the
``codex exec`` subcommand (Codex's non-interactive entry point).

Non-interactive guarantees:
    - ``codex exec`` subcommand (one-shot, never opens the TUI).
    - ``--skip-git-repo-check`` so missing-repo doesn't abort the run.
    - ``--sandbox read-only`` keeps the sandbox tight — we're using
      codex as a chat backend, not letting it write to the workspace.
    - ``stdin=DEVNULL`` and a hard timeout via the shared transport.

Image attachment: ``codex exec`` accepts ``-i <FILE>`` (repeatable) for
native image input.
"""

from __future__ import annotations

import os
import shutil
import uuid
from collections import deque
from collections.abc import Iterator, Mapping
from typing import Any

from harnesses.base import Harness, HarnessError, HarnessStatus
from harnesses.cli_common import CliError, run_blocking, stream_pty


class CodexCliHarness(Harness):
    """Shell out to the installed ``codex`` binary.

    Config keys:
        binary:     Path or name of the binary. Defaults to ``"codex"``.
        model:      Default model id (passed as ``--model``).
        timeout:    Wall-clock timeout in seconds (default 180 — code
                    tasks tend to be slow).
        sandbox:    Sandbox mode for ``codex exec``. Default
                    ``"read-only"``; override only if you specifically
                    need codex to write to the workspace.
        extra_args: List of extra argv entries.
    """

    name = "codex_cli"

    def __init__(self, config: Mapping[str, Any] | None = None) -> None:
        super().__init__(config)
        self._binary_override: str | None = self.config.get("binary")
        self.model: str | None = self.config.get("model")
        self.timeout: float = float(self.config.get("timeout", 180))
        self.sandbox: str = str(self.config.get("sandbox", "read-only"))
        self.extra_args: list[str] = list(self.config.get("extra_args", []))
        self._request_ids: deque[str] = deque(maxlen=64)
        self._resolved_binary: str | None = None

    # ----------------------------------------------------------------- internals
    def _resolve_binary(self) -> str:
        if self._resolved_binary is not None:
            return self._resolved_binary
        candidate = self._binary_override or "codex"
        if os.path.isabs(candidate):
            if not os.path.isfile(candidate) or not os.access(candidate, os.X_OK):
                raise HarnessError(f"codex binary not executable: {candidate}")
            self._resolved_binary = candidate
            return candidate
        found = shutil.which(candidate)
        if not found:
            raise HarnessError(
                f"could not locate {candidate!r} on PATH — install Codex CLI or set "
                "config['binary'] to the absolute path"
            )
        self._resolved_binary = found
        return found

    def _build_argv(self, request: Mapping[str, Any]) -> list[str]:
        prompt = self._render_prompt(request)
        argv: list[str] = [
            self._resolve_binary(),
            "exec",
            "--skip-git-repo-check",
            "--sandbox",
            self.sandbox,
            "--color",
            "never",
        ]
        model = request.get("model") or self.model
        if model:
            argv.extend(["--model", str(model)])
        for img in request.get("images") or []:
            argv.extend(["--image", str(img)])
        argv.extend(self.extra_args)
        argv.append(prompt)
        return argv

    @staticmethod
    def _render_prompt(request: Mapping[str, Any]) -> str:
        base = request.get("prompt")
        if base is None:
            messages = request.get("messages") or []
            base = "\n\n".join(
                str(m.get("content", "")) for m in messages if isinstance(m, dict)
            )
        return str(base or "").rstrip()

    # ----------------------------------------------------------------- lifecycle
    def start(self) -> HarnessStatus:
        self._resolve_binary()
        return self._set_state("running", f"binary={self._resolved_binary}")

    def stop(self) -> HarnessStatus:
        return self._set_state("stopped")

    def status(self) -> HarnessStatus:
        return HarnessStatus(
            name=self.name,
            state=self._state,
            detail=f"binary={self._resolved_binary or self._binary_override or 'codex'} sandbox={self.sandbox}",
            metadata={"model": self.model, "request_ids": list(self._request_ids)},
        )

    # ------------------------------------------------------------------ requests
    def invoke(self, request: Mapping[str, Any]) -> dict[str, Any]:
        argv = self._build_argv(request)
        timeout = float(request.get("timeout", self.timeout))
        try:
            completed = run_blocking(argv, timeout=timeout)
        except CliError as exc:
            self._record(f"invoke error: {exc}")
            raise HarnessError(f"codex_cli invoke failed: {exc}") from exc
        rid = uuid.uuid4().hex
        self._request_ids.append(rid)
        self._record(f"invoke ok id={rid}")
        return {
            "id": rid,
            "model": request.get("model") or self.model or "",
            "text": completed.stdout,
            "stderr": completed.stderr,
            "returncode": completed.returncode,
        }

    def stream(self, request: Mapping[str, Any]) -> Iterator[dict[str, Any]]:
        argv = self._build_argv(request)
        timeout = float(request.get("timeout", self.timeout))
        try:
            for chunk in stream_pty(argv, timeout=timeout):
                yield {"text": chunk}
            self._record("stream ok")
        except CliError as exc:
            self._record(f"stream error: {exc}")
            raise HarnessError(f"codex_cli stream failed: {exc}") from exc

    # ---------------------------------------------------------------- observers
    def logs(self, tail: int = 50) -> list[str]:
        return list(self._logs)[-tail:]

    def health(self) -> HarnessStatus:
        try:
            binary = self._resolve_binary()
        except HarnessError as exc:
            return HarnessStatus(name=self.name, state="error", detail=str(exc))
        try:
            run_blocking([binary, "--version"], timeout=5)
        except CliError as exc:
            return HarnessStatus(
                name=self.name,
                state="error",
                detail=f"codex --version failed: {exc.stderr or exc.returncode}",
            )
        return HarnessStatus(name=self.name, state="ready", detail=f"binary={binary}")
