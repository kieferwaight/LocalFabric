"""Definition and InputConstraint dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class InputConstraint:
    type: str = "string"
    required: bool = False
    default: Any = None
    description: str = ""

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "InputConstraint":
        allowed = {"string", "number", "boolean", "array"}
        t = raw.get("type", "string")
        if t not in allowed:
            raise ValueError(f"Unsupported input type: {t!r}")
        return cls(
            type=t,
            required=bool(raw.get("required", False)),
            default=raw.get("default", None),
            description=str(raw.get("description", "")),
        )


@dataclass
class Definition:
    id: str
    extends: Optional[str] = None
    mixins: List[str] = field(default_factory=list)
    run: List[Dict[str, str]] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    inputs: Dict[str, InputConstraint] = field(default_factory=dict)
    teardown: List[Dict[str, str]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "Definition":
        if "id" not in raw:
            raise ValueError("Definition is missing required 'id' field.")
        inputs_raw = raw.get("inputs") or {}
        inputs = {k: InputConstraint.from_dict(v or {}) for k, v in inputs_raw.items()}
        return cls(
            id=str(raw["id"]),
            extends=raw.get("extends"),
            mixins=list(raw.get("mixins") or []),
            run=list(raw.get("run") or []),
            variables=dict(raw.get("variables") or {}),
            inputs=inputs,
            teardown=list(raw.get("teardown") or []),
        )
