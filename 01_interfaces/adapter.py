"""
Adapter interface — Python Protocol for 03_adapters.

Adapters translate an external interface (CLI args, REST body, OpenAI
chat completion request, MCP tool call) into the internal Request shape
defined by dispatch.request.schema.yaml. Adapters are stateless.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class AdapterProtocol(Protocol):
    def to_request(self, external: Any) -> dict[str, Any]:
        """Translate the inbound external payload to the internal Request schema."""
        ...

    def from_response(self, response: dict[str, Any]) -> Any:
        """Translate an internal Response into the external interface's reply shape."""
        ...
