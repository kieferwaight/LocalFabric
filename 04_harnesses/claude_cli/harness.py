"""Harness for the locally installed ``claude`` CLI (Claude Code).

This is a parallel transport channel to ``harnesses.claude.ClaudeHarness``
(SDK) — same interface, different connection. Use this when you want
the user's local ``claude`` binary to handle prompts (and so it picks up
any local config the user has set up), rather than calling the
Anthropic Messages API directly.

Non-interactive guarantees:
    - ``--print`` (one-shot mode; workspace-trust dialog is auto-skipped).
    - ``--permission-mode bypassPermissions`` so tool-use prompts never block.
    - ``stdin=DEVNULL`` and a hard wall-clock timeout via the shared
      transport.

Image attachment: paths in the request's ``images`` list are spliced
into the prompt body as Claude ``@<path>`` mentions, and the parent
directory of each path is appended to ``--add-dir`` so the CLI is
allowed to read it. This relies on the Read tool being available in
``--print`` mode; ``--allowed-tools`` is not narrowed here so Claude
can fetch the file.
"""

from __future__ import annotations

import os
import shutil
import uuid
from collections import deque
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

from harnesses.base import Harness, HarnessError, HarnessStatus
from harnesses.cli_common import CliError, run_blocking, stream_pty


class ClaudeCliHarness(Harness):
    """Shell out to the installed ``claude`` binary.

    Config keys:
        binary:     Path or name of the binary. Defaults to ``"claude"`` and
                    is resolved via ``shutil.which``.
        model:      Default model id (passed as ``--model``).
        timeout:    Wall-clock timeout in seconds (default 120).
        extra_args: List of extra argv entries appended after the
                    standard non-interactive flags.
    """

    name = "claude_cli"

    def __init__(self, config: Mapping[str, Any] | None = None) -> None:
        super().__init__(config)
        self._binary_override: str | None = self.config.get("binary")
        self.model: str | None = self.config.get("model")
        self.timeout: float = float(self.config.get("timeout", 120))
        self.extra_args: list[str] = list(self.config.get("extra_args", []))
        self._request_ids: deque[str] = deque(maxlen=64)
        self._resolved_binary: str | None = None

    # ----------------------------------------------------------------- internals
    def _resolve_binary(self) -> str:
        if self._resolved_binary is not None:
            return self._resolved_binary
        candidate = self._binary_override or "claude"
        if os.path.isabs(candidate):
            if not os.path.isfile(candidate) or not os.access(candidate, os.X_OK):
                raise HarnessError(f"claude binary not executable: {candidate}")
            self._resolved_binary = candidate
            return candidate
        found = shutil.which(candidate)
        if not found:
            raise HarnessError(
                f"could not locate {candidate!r} on PATH — install Claude Code or set "
                "config['binary'] to the absolute path"
            )
        self._resolved_binary = found
        return found

    def _build_argv(self, request: Mapping[str, Any]) -> list[str]:
        prompt = self._render_prompt(request)
        argv: list[str] = [self._resolve_binary()]

        # `--add-dir <directories...>` is variadic per `claude --help` — if
        # anything other than another `--flag` follows it, commander.js
        # swallows it as another directory. Emit these first so the
        # immediately following `--print` terminates the variadic cleanly.
        for parent in self._image_parents(request.get("images") or []):
            argv.extend(["--add-dir", parent])

        argv.extend(
            [
                "--print",
                "--permission-mode",
                "bypassPermissions",
                "--output-format",
                "text",
            ]
        )
        model = request.get("model") or self.model
        if model:
            argv.extend(["--model", str(model)])
        argv.extend(self.extra_args)
        argv.append(prompt)
        return argv

    @staticmethod
    def _render_prompt(request: Mapping[str, Any]) -> str:
        """Compose the prompt body, splicing in ``@<path>`` mentions for images."""
        base = request.get("prompt")
        if base is None:
            messages = request.get("messages") or []
            base = "\n\n".join(
                str(m.get("content", "")) for m in messages if isinstance(m, dict)
            )
        body = str(base or "").rstrip()
        images = request.get("images") or []
        if images:
            mentions = "\n".join(f"@{p}" for p in images)
            body = f"{body}\n\n{mentions}" if body else mentions
        return body

    @staticmethod
    def _image_parents(images: list[str]) -> list[str]:
        seen: list[str] = []
        for path in images:
            parent = str(Path(path).expanduser().resolve().parent)
            if parent not in seen:
                seen.append(parent)
        return seen

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
            detail=f"binary={self._resolved_binary or self._binary_override or 'claude'}",
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
            raise HarnessError(f"claude_cli invoke failed: {exc}") from exc
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
            raise HarnessError(f"claude_cli stream failed: {exc}") from exc

    # ---------------------------------------------------------------- observers
    def logs(self, tail: int = 50) -> list[str]:
        return list(self._logs)[-tail:]

    def health(self) -> HarnessStatus:
        """Cheap health probe: ``which`` + ``claude --version``. No tokens spent."""
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
                detail=f"claude --version failed: {exc.stderr or exc.returncode}",
            )
        return HarnessStatus(name=self.name, state="ready", detail=f"binary={binary}")
