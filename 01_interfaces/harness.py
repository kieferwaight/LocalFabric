"""
Harness interface — Python Protocol mirror of 04_harnesses/base.Harness.

Adapters/routers can depend on this Protocol without pulling the full
harness package. The concrete ABC lives in 04_harnesses/base.py.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class HarnessProtocol(Protocol):
    """Execution-lifecycle contract for a provider, tool, or service."""

    def start(self) -> None: ...
    def stop(self) -> None: ...
    def status(self) -> dict[str, Any]: ...
    def invoke(self, prompt: str, **kwargs: Any) -> str: ...
    def stream(self, prompt: str, **kwargs: Any) -> Iterator[dict[str, Any]]: ...
    def logs(self, tail: int = 50) -> list[str]: ...
    def health(self) -> bool: ...
