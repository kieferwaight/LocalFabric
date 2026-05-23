"""Lexically scoped variable frames with parent-pointer lookup."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .shell_environment import ShellEnvironment


@dataclass
class ScopeFrame:
    parent: Optional["ScopeFrame"] = None
    local_store: Dict[str, Any] = field(default_factory=dict)

    def set(self, key: str, val: Any) -> None:
        self.local_store[key] = val

    def update(self, mapping: Dict[str, Any]) -> None:
        self.local_store.update(mapping)

    def resolve(self, key: str) -> Any:
        frame: Optional[ScopeFrame] = self
        while frame is not None:
            if key in frame.local_store:
                return frame.local_store[key]
            frame = frame.parent
        raise KeyError(key)

    def flatten(self) -> Dict[str, Any]:
        """Collect all variables walking up the parent chain. Child wins."""
        merged: Dict[str, Any] = {}
        chain = []
        frame: Optional[ScopeFrame] = self
        while frame is not None:
            chain.append(frame)
            frame = frame.parent
        for f in reversed(chain):
            merged.update(f.local_store)
        return merged

    def build_jinja_context(
        self, globals_: Dict[str, Any], env: "ShellEnvironment"
    ) -> Dict[str, Any]:
        merged: Dict[str, Any] = {}
        merged.update(globals_)
        merged.update(self.flatten())
        merged["env"] = env.to_dict()
        merged["runtime"] = globals_
        return merged
