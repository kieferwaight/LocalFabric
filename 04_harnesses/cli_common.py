"""Shared subprocess transport for the CLI-backed harnesses.

This module owns process lifecycle and stdio plumbing only — no UI. The
spinner that wraps long-running calls lives in
``core.interfaces.cli.spinner`` and is invoked by the markdown-runtime
CLI, not by the transport layer. Keeping these two concerns apart
guarantees that exactly one writer ever touches ``/dev/tty``.

The non-streaming path uses :func:`subprocess.run` with separate
stdout/stderr capture and ``stdin=DEVNULL`` so the child can never block
on a read. The streaming path allocates a pseudo-terminal via the stdlib
:mod:`pty` module so the child flushes per token instead of waiting for
its 4 KB pipe buffer to fill — without a PTY, agentic CLIs like
``claude`` and ``gemini`` will stutter or hang under plain
``Popen.stdout`` reads. PTYs are POSIX-only; the streaming entry point
raises a clear error on Windows.
"""

from __future__ import annotations

import errno
import os
import select
import signal
import subprocess
import sys
import threading
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass


class CliError(RuntimeError):
    """Raised by the transport when a subprocess exits non-zero or times out.

    Carries the full argv, exit code, and captured stderr so callers can
    wrap it in a domain-specific error (``HarnessError`` /
    ``ProviderError``) without losing diagnostic detail.
    """

    def __init__(self, *, returncode: int, stderr: str, argv: Sequence[str]) -> None:
        self.returncode = returncode
        self.stderr = stderr
        self.argv = list(argv)
        joined = " ".join(argv)
        detail = stderr.strip() or f"exit {returncode}"
        super().__init__(f"{joined!s}: {detail}")


@dataclass(frozen=True)
class CompletedRun:
    """Result of a blocking subprocess invocation."""

    returncode: int
    stdout: str
    stderr: str


def _start_new_session() -> None:
    """Pre-exec hook that puts the child in its own process group.

    Used so the timeout path can kill the whole group (the binary plus
    anything it spawned) instead of leaving zombies behind.
    """
    os.setsid()


def run_blocking(
    argv: Sequence[str],
    *,
    timeout: float | None = None,
    cwd: str | None = None,
    env: Mapping[str, str] | None = None,
) -> CompletedRun:
    """Spawn ``argv`` and wait for it to finish.

    Stdin is closed; stdout and stderr are captured separately so the
    caller can return one as the result text and the other as
    diagnostic detail. A timeout kills the entire process group rather
    than just the leader.

    Raises :class:`CliError` on non-zero exit or timeout. The error's
    ``stderr`` always carries the captured diagnostics — never mixed
    with stdout — so the caller can decide which stream to surface.
    """
    try:
        proc = subprocess.Popen(  # noqa: S603 — argv is a list, never a shell string
            list(argv),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            env=dict(env) if env is not None else None,
            preexec_fn=_start_new_session if os.name == "posix" else None,
            text=True,
        )
    except FileNotFoundError as exc:
        raise CliError(returncode=127, stderr=str(exc), argv=argv) from exc

    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        _kill_group(proc)
        # Drain whatever is buffered so the caller sees partial output.
        stdout, stderr = proc.communicate()
        raise CliError(
            returncode=124,
            stderr=(stderr or "") + f"\n[timed out after {timeout}s]",
            argv=argv,
        ) from None

    if proc.returncode != 0:
        raise CliError(returncode=proc.returncode, stderr=stderr or "", argv=argv)

    return CompletedRun(returncode=proc.returncode, stdout=stdout or "", stderr=stderr or "")


def stream_pty(
    argv: Sequence[str],
    *,
    timeout: float | None = None,
    cwd: str | None = None,
    env: Mapping[str, str] | None = None,
    chunk_size: int = 1024,
) -> Iterator[str]:
    """Spawn ``argv`` attached to a PTY and yield stdout chunks as they arrive.

    A pseudo-terminal is allocated via :func:`pty.openpty`; the child's
    stdout is attached to the slave fd, so libc keeps it line-buffered
    instead of switching to 4 KB block buffering as it would on a plain
    pipe. The master fd is read in non-blocking chunks and decoded as
    UTF-8 (with ``errors='replace'`` so a stray byte never breaks the
    stream).

    Stderr is captured to a separate pipe in a background thread and
    surfaced via :class:`CliError` on non-zero exit. A timeout kills the
    process group.

    POSIX-only. Raises :class:`CliError` with a clear message on Windows.
    """
    if os.name != "posix":
        raise CliError(
            returncode=1,
            stderr="stream_pty is POSIX-only; Windows is not supported in v1",
            argv=argv,
        )

    import pty  # local import — stdlib but POSIX-only

    master_fd, slave_fd = pty.openpty()
    stderr_buf: list[str] = []
    proc: subprocess.Popen[str] | None = None

    try:
        try:
            proc = subprocess.Popen(  # noqa: S603 — argv is a list
                list(argv),
                stdin=subprocess.DEVNULL,
                stdout=slave_fd,
                stderr=subprocess.PIPE,
                cwd=cwd,
                env=dict(env) if env is not None else None,
                preexec_fn=_start_new_session,
                close_fds=True,
                text=False,
            )
        except FileNotFoundError as exc:
            raise CliError(returncode=127, stderr=str(exc), argv=argv) from exc

        # Slave end belongs to the child; close our copy or reads block forever.
        os.close(slave_fd)
        slave_fd = -1

        stderr_thread = threading.Thread(
            target=_drain_stderr,
            args=(proc.stderr, stderr_buf),
            daemon=True,
        )
        stderr_thread.start()

        yield from _read_master_until_exit(
            master_fd=master_fd,
            proc=proc,
            timeout=timeout,
            chunk_size=chunk_size,
            argv=argv,
            stderr_buf=stderr_buf,
        )

        stderr_thread.join(timeout=1.0)
        if proc.returncode != 0:
            raise CliError(
                returncode=proc.returncode,
                stderr="".join(stderr_buf),
                argv=argv,
            )
    finally:
        if slave_fd >= 0:
            _safe_close(slave_fd)
        _safe_close(master_fd)
        if proc is not None and proc.poll() is None:
            _kill_group(proc)


def _read_master_until_exit(
    *,
    master_fd: int,
    proc: subprocess.Popen[bytes],
    timeout: float | None,
    chunk_size: int,
    argv: Sequence[str],
    stderr_buf: list[str],
) -> Iterator[str]:
    """Drain the PTY master until the child exits or a timeout fires."""
    import time

    deadline = (time.monotonic() + timeout) if timeout is not None else None

    while True:
        remaining = None
        if deadline is not None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                _kill_group(proc)
                proc.wait(timeout=2)
                raise CliError(
                    returncode=124,
                    stderr="".join(stderr_buf) + f"\n[timed out after {timeout}s]",
                    argv=argv,
                )

        # select() with a short cap keeps the timeout check responsive
        # even when the child is silent for long stretches.
        wait_for = 0.5 if remaining is None else min(0.5, remaining)
        try:
            ready, _, _ = select.select([master_fd], [], [], wait_for)
        except (OSError, ValueError):
            ready = []

        if ready:
            try:
                data = os.read(master_fd, chunk_size)
            except OSError as exc:
                # EIO arrives on Linux when the child closes the slave;
                # treat as EOF.
                if exc.errno == errno.EIO:
                    data = b""
                else:
                    raise
            if not data:
                # EOF on master — child has closed its stdout. Wait for
                # the process to actually exit so we have a returncode.
                proc.wait()
                return
            yield data.decode("utf-8", errors="replace")
            continue

        if proc.poll() is not None:
            # Process exited while we were idle. Drain anything still in
            # the PTY buffer, then return.
            try:
                while True:
                    data = os.read(master_fd, chunk_size)
                    if not data:
                        break
                    yield data.decode("utf-8", errors="replace")
            except OSError:
                pass
            return


def _drain_stderr(stream: object, buffer: list[str]) -> None:
    """Background thread that collects the child's stderr into ``buffer``."""
    if stream is None:
        return
    try:
        for chunk in iter(lambda: stream.read(4096), b""):  # type: ignore[attr-defined]
            if not chunk:
                break
            if isinstance(chunk, bytes):
                buffer.append(chunk.decode("utf-8", errors="replace"))
            else:
                buffer.append(chunk)
    except (OSError, ValueError):
        pass
    finally:
        try:
            stream.close()  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass


def _kill_group(proc: subprocess.Popen[object]) -> None:
    """Kill ``proc`` and every child it spawned. Best-effort, no raise."""
    if proc.pid <= 0:
        return
    try:
        if os.name == "posix":
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        else:
            proc.kill()
    except (ProcessLookupError, PermissionError, OSError):
        pass


def _safe_close(fd: int) -> None:
    try:
        os.close(fd)
    except OSError:
        pass


# Re-exported for type checkers that import from a single namespace.
__all__ = ["CliError", "CompletedRun", "run_blocking", "stream_pty"]


def _is_windows() -> bool:  # pragma: no cover - trivial
    return sys.platform.startswith("win")
