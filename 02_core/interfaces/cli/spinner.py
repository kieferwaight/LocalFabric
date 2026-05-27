"""Terminal spinner for blocking provider calls.

Lives in the UI layer so the transport layer
(:mod:`harnesses.cli_common`) doesn't also need to know about
``/dev/tty`` — exactly one writer touches the controlling terminal,
which is what keeps the output from flickering or fragmenting.

Ports the ``/dev/tty`` + isatty-check pattern from the bash example at
``15_examples/code.summarize.example.md``. When no controlling tty is
attached (CI, piped output, stdin/stdout redirected), the spinner
silently degrades to a no-op so it never lands in captured streams.
"""

from __future__ import annotations

import os
import threading
import time
from types import TracebackType


_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]


class Spinner:
    """Context manager that prints a braille spinner to ``/dev/tty``.

    Usage::

        with Spinner("Asking claude_cli…"):
            result = harness.invoke(request)

    The spinner writes to ``/dev/tty`` from a background daemon thread
    so it doesn't pollute stdout (which the caller is likely returning
    as the prompt result) or stderr (which carries error diagnostics).
    If ``/dev/tty`` cannot be opened — e.g. the process is running
    without a controlling terminal — entering the context manager is a
    no-op.
    """

    def __init__(self, message: str, *, interval: float = 0.1) -> None:
        self.message = message
        self.interval = interval
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._tty: object | None = None  # open file object for /dev/tty

    def __enter__(self) -> Spinner:
        tty = _open_tty()
        if tty is None:
            return self
        self._tty = tty
        # Hide the cursor while the spinner runs.
        try:
            tty.write("\033[?25l")
            tty.flush()
        except OSError:
            self._close_tty()
            return self
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None
        if self._tty is not None:
            try:
                # Clear the line and restore the cursor.
                self._tty.write("\r\033[2K\033[?25h")
                self._tty.flush()
            except OSError:
                pass
            self._close_tty()

    def _loop(self) -> None:
        assert self._tty is not None
        i = 0
        while not self._stop.is_set():
            frame = _FRAMES[i % len(_FRAMES)]
            try:
                self._tty.write(f"\r\033[2K{frame} {self.message}")
                self._tty.flush()
            except OSError:
                return
            i += 1
            if self._stop.wait(self.interval):
                return

    def _close_tty(self) -> None:
        if self._tty is None:
            return
        try:
            self._tty.close()  # type: ignore[attr-defined]
        except OSError:
            pass
        self._tty = None


def _open_tty():
    """Open ``/dev/tty`` for writing, or return ``None`` if no tty exists.

    Bypasses ``sys.stdout`` so the spinner never lands in captured output
    when the caller is piping the program's stdout into another process.
    """
    if os.name != "posix":
        return None
    try:
        return open("/dev/tty", "w", encoding="utf-8", buffering=1)
    except OSError:
        return None


__all__ = ["Spinner"]
