"""Tests for the Spinner context manager.

Verifies the spinner never writes to stdout/stderr (it must go to
``/dev/tty`` only), and that absence of a controlling terminal is a
silent no-op rather than a crash.
"""

from __future__ import annotations

import io
import sys

import pytest

from core.interfaces.cli.spinner import Spinner


def test_spinner_no_tty_is_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    """When ``_open_tty`` returns ``None``, entering the spinner is harmless."""
    monkeypatch.setattr("core.interfaces.cli.spinner._open_tty", lambda: None)
    captured_out = io.StringIO()
    captured_err = io.StringIO()
    monkeypatch.setattr(sys, "stdout", captured_out)
    monkeypatch.setattr(sys, "stderr", captured_err)
    with Spinner("Working…"):
        pass
    assert captured_out.getvalue() == ""
    assert captured_err.getvalue() == ""


def test_spinner_writes_to_provided_tty(monkeypatch: pytest.MonkeyPatch) -> None:
    """When a fake tty is provided, the spinner thread writes frames to it."""
    fake_tty = io.StringIO()
    # Defang close() so the Spinner's cleanup doesn't invalidate the buffer
    # before the test inspects it.
    monkeypatch.setattr(fake_tty, "close", lambda: None)
    monkeypatch.setattr("core.interfaces.cli.spinner._open_tty", lambda: fake_tty)
    with Spinner("Pinging…", interval=0.01):
        import time

        time.sleep(0.05)
    output = fake_tty.getvalue()
    assert "Pinging" in output
    # Cursor restoration sequence is emitted on exit.
    assert "\033[?25h" in output


def test_spinner_does_not_touch_stdout_when_tty_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_tty = io.StringIO()
    monkeypatch.setattr("core.interfaces.cli.spinner._open_tty", lambda: fake_tty)
    captured_out = io.StringIO()
    captured_err = io.StringIO()
    monkeypatch.setattr(sys, "stdout", captured_out)
    monkeypatch.setattr(sys, "stderr", captured_err)
    with Spinner("Working…", interval=0.01):
        import time

        time.sleep(0.03)
    assert captured_out.getvalue() == ""
    assert captured_err.getvalue() == ""
