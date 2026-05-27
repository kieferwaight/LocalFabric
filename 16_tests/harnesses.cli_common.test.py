"""Tests for the shared CLI subprocess transport.

Exercises ``run_blocking`` and ``stream_pty`` against real Python child
processes — including a deliberately slow child for the PTY streaming
test, which is the case that would block-buffer (and thus stutter or
hang) under plain ``Popen.stdout``.
"""

from __future__ import annotations

import os
import sys
import textwrap

import pytest

from harnesses.cli_common import CliError, run_blocking, stream_pty


# ---------------------------------------------------------------------------
# run_blocking
# ---------------------------------------------------------------------------


def test_run_blocking_happy_path() -> None:
    completed = run_blocking([sys.executable, "-c", "print('hi')"])
    assert completed.returncode == 0
    assert completed.stdout.strip() == "hi"
    assert completed.stderr == ""


def test_run_blocking_captures_stderr_separately() -> None:
    completed = run_blocking(
        [
            sys.executable,
            "-c",
            "import sys; print('out'); print('err', file=sys.stderr)",
        ]
    )
    assert completed.stdout.strip() == "out"
    assert completed.stderr.strip() == "err"


def test_run_blocking_nonzero_exit_raises_cli_error() -> None:
    with pytest.raises(CliError) as exc_info:
        run_blocking([sys.executable, "-c", "import sys; sys.exit(2)"])
    assert exc_info.value.returncode == 2


def test_run_blocking_error_carries_stderr() -> None:
    with pytest.raises(CliError) as exc_info:
        run_blocking(
            [
                sys.executable,
                "-c",
                "import sys; sys.stderr.write('boom\\n'); sys.exit(3)",
            ]
        )
    assert "boom" in exc_info.value.stderr


def test_run_blocking_timeout_raises_cli_error_with_124() -> None:
    with pytest.raises(CliError) as exc_info:
        run_blocking(
            [sys.executable, "-c", "import time; time.sleep(5)"],
            timeout=0.2,
        )
    assert exc_info.value.returncode == 124
    assert "timed out" in exc_info.value.stderr


def test_run_blocking_missing_binary_raises_cli_error() -> None:
    with pytest.raises(CliError) as exc_info:
        run_blocking(["/no/such/binary-nope"])
    assert exc_info.value.returncode == 127


def test_run_blocking_closes_stdin() -> None:
    """Child reading stdin must see EOF immediately — no headless hang."""
    completed = run_blocking(
        [
            sys.executable,
            "-c",
            "import sys; data = sys.stdin.read(); print(f'read={len(data)}')",
        ],
        timeout=5,
    )
    assert completed.stdout.strip() == "read=0"


# ---------------------------------------------------------------------------
# stream_pty
# ---------------------------------------------------------------------------


@pytest.mark.skipif(os.name != "posix", reason="stream_pty is POSIX-only")
def test_stream_pty_yields_chunks_before_child_exits() -> None:
    """Without a PTY this child would block-buffer; with a PTY we see
    each line as it's printed.
    """
    src = textwrap.dedent(
        """
        import sys, time
        for i in range(3):
            sys.stdout.write(f'line{i}\\n')
            sys.stdout.flush()
            time.sleep(0.05)
        """
    ).strip()
    chunks: list[str] = []
    for chunk in stream_pty([sys.executable, "-c", src], timeout=10):
        chunks.append(chunk)
    joined = "".join(chunks)
    assert "line0" in joined
    assert "line1" in joined
    assert "line2" in joined


@pytest.mark.skipif(os.name != "posix", reason="stream_pty is POSIX-only")
def test_stream_pty_raises_on_nonzero_exit() -> None:
    src = textwrap.dedent(
        """
        import sys
        sys.stderr.write('bad\\n')
        sys.exit(7)
        """
    ).strip()
    with pytest.raises(CliError) as exc_info:
        list(stream_pty([sys.executable, "-c", src], timeout=5))
    assert exc_info.value.returncode == 7


@pytest.mark.skipif(os.name != "posix", reason="stream_pty is POSIX-only")
def test_stream_pty_timeout_kills_child() -> None:
    src = "import time; time.sleep(30)"
    with pytest.raises(CliError) as exc_info:
        list(stream_pty([sys.executable, "-c", src], timeout=0.3))
    assert exc_info.value.returncode == 124


@pytest.mark.skipif(os.name != "posix", reason="stream_pty is POSIX-only")
def test_stream_pty_missing_binary_raises() -> None:
    with pytest.raises(CliError) as exc_info:
        list(stream_pty(["/no/such/binary-nope"]))
    assert exc_info.value.returncode == 127


# ---------------------------------------------------------------------------
# CliError
# ---------------------------------------------------------------------------


def test_cli_error_message_includes_argv_and_stderr() -> None:
    err = CliError(returncode=2, stderr="oops", argv=["a", "b"])
    msg = str(err)
    assert "a b" in msg
    assert "oops" in msg
