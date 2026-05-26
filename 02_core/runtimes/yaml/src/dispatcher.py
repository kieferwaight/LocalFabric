"""Polyglot subprocess dispatcher with IPC state bridge."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from typing import Any

LANGUAGE_BINARIES: dict[str, list[str]] = {
    "bash": ["/usr/bin/env", "bash"],
    "sh": ["/usr/bin/env", "sh"],
    "js": ["/usr/bin/env", "node"],
    "javascript": ["/usr/bin/env", "node"],
    "python": ["/usr/bin/env", "python3"],
    "py": ["/usr/bin/env", "python3"],
}


@dataclass
class DispatchResult:
    language: str
    exit_code: int
    stdout: str
    stderr: str
    state_updates: dict[str, Any]


class Dispatcher:
    """Executes a block by writing the rendered source to a temp file and shelling out."""

    def __init__(self, language_binaries: dict[str, list[str]] | None = None) -> None:
        self.language_binaries = dict(LANGUAGE_BINARIES)
        if language_binaries:
            self.language_binaries.update(language_binaries)

    def supports(self, language: str) -> bool:
        return language in self.language_binaries

    def dispatch(
        self,
        language: str,
        source: str,
        base_env: dict[str, str] | None = None,
        cwd: str | None = None,
    ) -> DispatchResult:
        if language not in self.language_binaries:
            raise ValueError(f"Unsupported language: {language!r}")

        binary = self.language_binaries[language]
        suffix = {
            "bash": ".sh",
            "sh": ".sh",
            "js": ".js",
            "javascript": ".js",
            "python": ".py",
            "py": ".py",
        }.get(language, "")

        env = dict(os.environ if base_env is None else base_env)
        state_fd, state_path = tempfile.mkstemp(prefix="yrt-state-", suffix=".json")
        os.close(state_fd)
        # Pre-seed with empty object so subprocess can read it idempotently.
        with open(state_path, "w", encoding="utf-8") as fh:
            fh.write("{}")
        env["STATE_FILE"] = state_path

        script_fd, script_path = tempfile.mkstemp(prefix="yrt-script-", suffix=suffix)
        os.close(script_fd)
        with open(script_path, "w", encoding="utf-8") as fh:
            fh.write(source)

        try:
            cmd = list(binary) + [script_path]
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                cwd=cwd,
                text=True,
                bufsize=1,
            )
            stdout_chunks: list[str] = []
            stderr_chunks: list[str] = []
            # Stream stderr live; capture stdout to a buffer.
            assert proc.stdout is not None and proc.stderr is not None
            try:
                while True:
                    err_line = proc.stderr.readline()
                    if err_line:
                        stderr_chunks.append(err_line)
                        sys.stderr.write(err_line)
                        sys.stderr.flush()
                    out_line = proc.stdout.readline()
                    if out_line:
                        stdout_chunks.append(out_line)
                    if not err_line and not out_line and proc.poll() is not None:
                        break
                rem_out, rem_err = proc.communicate()
                if rem_out:
                    stdout_chunks.append(rem_out)
                if rem_err:
                    stderr_chunks.append(rem_err)
                    sys.stderr.write(rem_err)
                    sys.stderr.flush()
            except KeyboardInterrupt:
                proc.kill()
                raise

            stdout = "".join(stdout_chunks)
            stderr = "".join(stderr_chunks)
            exit_code = proc.returncode if proc.returncode is not None else -1

            state_updates: dict[str, Any] = {}
            # First check the state file (preferred channel).
            try:
                with open(state_path, encoding="utf-8") as fh:
                    text = fh.read().strip()
                if text:
                    parsed = json.loads(text)
                    if isinstance(parsed, dict):
                        state_updates.update(parsed)
            except (FileNotFoundError, json.JSONDecodeError):
                pass
            # Then attempt to merge JSON-only stdout, for blocks that just print.
            stripped_stdout = stdout.strip()
            if stripped_stdout:
                try:
                    parsed = json.loads(stripped_stdout)
                    if isinstance(parsed, dict):
                        for k, v in parsed.items():
                            state_updates.setdefault(k, v)
                except json.JSONDecodeError:
                    pass

            if exit_code != 0:
                tail = "\n".join(stderr.strip().splitlines()[-20:])
                raise RuntimeError(
                    f"Subprocess block ({language}) exited with code {exit_code}.\n"
                    f"stderr tail:\n{tail}"
                )

            return DispatchResult(
                language=language,
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                state_updates=state_updates,
            )
        finally:
            for path in (state_path, script_path):
                try:
                    os.unlink(path)
                except OSError:
                    pass
