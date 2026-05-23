"""Abstract base class for all harnesses. Defines the lifecycle contract."""

from __future__ import annotations

import abc
import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, Iterator, Mapping, Optional


class HarnessError(RuntimeError):
    """Raised for harness-level failures (start/stop/invoke/health)."""


@dataclass
class HarnessStatus:
    """Snapshot of a harness's lifecycle state."""

    name: str
    state: str  # "stopped" | "starting" | "running" | "degraded" | "error"
    detail: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def ok(self) -> bool:
        return self.state in {"running", "ready"}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "state": self.state,
            "detail": self.detail,
            "metadata": dict(self.metadata),
        }


class Harness(abc.ABC):
    """Lifecycle controller for a single provider, model, or service.

    Concrete subclasses implement the seven required methods. The base class
    provides a small log buffer and a default `name` derived from the class.
    """

    #: Default human-readable name (subclasses may override).
    name: str = "harness"

    #: How many recent log lines to retain in memory.
    log_buffer_size: int = 256

    def __init__(self, config: Optional[Mapping[str, Any]] = None) -> None:
        self.config: Dict[str, Any] = dict(config or {})
        self._state: str = "stopped"
        self._logs: Deque[str] = deque(maxlen=self.log_buffer_size)
        self._logger = logging.getLogger(f"harness.{self.name}")

    # ------------------------------------------------------------------ helpers
    def _set_state(self, state: str, detail: str = "") -> HarnessStatus:
        self._state = state
        snap = HarnessStatus(name=self.name, state=state, detail=detail)
        self._record(f"state -> {state} ({detail})" if detail else f"state -> {state}")
        return snap

    def _record(self, line: str) -> None:
        self._logs.append(line)
        self._logger.debug(line)

    # ----------------------------------------------------------------- contract
    @abc.abstractmethod
    def start(self) -> HarnessStatus:
        """Bring the harness into a running state. Idempotent."""

    @abc.abstractmethod
    def stop(self) -> HarnessStatus:
        """Tear the harness down cleanly. Idempotent."""

    @abc.abstractmethod
    def status(self) -> HarnessStatus:
        """Return the current lifecycle state without side effects."""

    @abc.abstractmethod
    def invoke(self, request: Mapping[str, Any]) -> Dict[str, Any]:
        """Execute a single request/response round trip."""

    @abc.abstractmethod
    def stream(self, request: Mapping[str, Any]) -> Iterator[Dict[str, Any]]:
        """Execute a request and yield incremental events."""

    @abc.abstractmethod
    def logs(self, tail: int = 50) -> list[str]:
        """Return the most recent log lines (default: last 50)."""

    @abc.abstractmethod
    def health(self) -> HarnessStatus:
        """Active health probe — may make a network or process check."""

    # ----------------------------------------------------------------- ergonomics
    def __enter__(self) -> "Harness":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.stop()

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"<{type(self).__name__} name={self.name!r} state={self._state!r}>"
