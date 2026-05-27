"""Tests for lib.shell.run_tests — run_local_tests.

subprocess.run is mocked so no real commands are executed.
"""

from __future__ import annotations

from subprocess import CompletedProcess, TimeoutExpired
from unittest.mock import patch

from lib.shell.run_tests import run_local_tests

# ---------------------------------------------------------------------------
# Happy path — all tests pass
# ---------------------------------------------------------------------------


def test_run_local_tests_success_message() -> None:
    with patch(
        "subprocess.run",
        return_value=CompletedProcess(args="pytest", returncode=0, stdout="10 passed", stderr=""),
    ):
        result = run_local_tests()
    assert "SUCCESS" in result
    assert "All tests passed" in result


def test_run_local_tests_includes_trimmed_stdout() -> None:
    stdout = "line1\nline2\n5 passed\n"
    with patch(
        "subprocess.run",
        return_value=CompletedProcess(args="pytest", returncode=0, stdout=stdout, stderr=""),
    ):
        result = run_local_tests()
    assert "passed" in result


def test_run_local_tests_default_command_is_pytest() -> None:
    with patch(
        "subprocess.run",
        return_value=CompletedProcess(args="pytest", returncode=0, stdout="ok", stderr=""),
    ) as mock_run:
        run_local_tests()
    call_args = mock_run.call_args
    assert "pytest" in call_args[0][0]


# ---------------------------------------------------------------------------
# Failure path
# ---------------------------------------------------------------------------


def test_run_local_tests_failure_message_on_nonzero_exit() -> None:
    stderr = "\n".join([f"ERROR line {i}" for i in range(35)])
    with patch(
        "subprocess.run",
        return_value=CompletedProcess(args="pytest", returncode=1, stdout="", stderr=stderr),
    ):
        result = run_local_tests()
    assert "FAILURE" in result
    assert "1" in result  # exit code


def test_run_local_tests_uses_stdout_when_stderr_empty() -> None:
    stdout = "\n".join([f"FAILED test_{i}" for i in range(35)])
    with patch(
        "subprocess.run",
        return_value=CompletedProcess(args="pytest", returncode=2, stdout=stdout, stderr=""),
    ):
        result = run_local_tests()
    assert "FAILURE" in result


def test_run_local_tests_trims_error_to_last_30_lines() -> None:
    stderr = "\n".join([f"line {i}" for i in range(100)])
    with patch(
        "subprocess.run",
        return_value=CompletedProcess(args="pytest", returncode=1, stdout="", stderr=stderr),
    ):
        result = run_local_tests()
    # Should not contain all 100 lines — last 30 only.
    # Check that the first line is NOT in the output.
    assert "line 0\n" not in result


# ---------------------------------------------------------------------------
# Timeout
# ---------------------------------------------------------------------------


def test_run_local_tests_timeout_message() -> None:
    with patch("subprocess.run", side_effect=TimeoutExpired(cmd="pytest", timeout=30)):
        result = run_local_tests()
    assert "timed out" in result.lower()
    assert "FAILURE" in result


# ---------------------------------------------------------------------------
# Custom command
# ---------------------------------------------------------------------------


def test_run_local_tests_custom_command() -> None:
    with patch(
        "subprocess.run",
        return_value=CompletedProcess(args="make test", returncode=0, stdout="ok", stderr=""),
    ) as mock_run:
        run_local_tests("make test")
    call_args = mock_run.call_args
    assert "make test" in call_args[0][0]


# ---------------------------------------------------------------------------
# General exception
# ---------------------------------------------------------------------------


def test_run_local_tests_exception_handled_gracefully() -> None:
    with patch("subprocess.run", side_effect=OSError("binary not found")):
        result = run_local_tests()
    assert "FAILURE" in result
    assert "binary not found" in result
