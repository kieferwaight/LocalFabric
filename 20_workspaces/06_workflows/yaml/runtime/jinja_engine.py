"""Multi-pass Jinja2 renderer used to expand variables and run blocks."""

from __future__ import annotations

from typing import Any, Dict

from jinja2 import Environment, StrictUndefined


class JinjaEngine:
    MAX_PASSES = 10

    def __init__(self, env: Environment | None = None) -> None:
        self.env = env or Environment(
            autoescape=False,
            keep_trailing_newline=True,
            undefined=StrictUndefined,
        )

    def render(self, source: str, context: Dict[str, Any]) -> str:
        if not isinstance(source, str):
            return source
        current = source
        for _ in range(self.MAX_PASSES):
            if "{{" not in current and "{%" not in current:
                return current
            template = self.env.from_string(current)
            rendered = template.render(**context)
            if rendered == current:
                return rendered
            current = rendered
        return current

    def render_value(self, value: Any, context: Dict[str, Any]) -> Any:
        if isinstance(value, str):
            return self.render(value, context)
        if isinstance(value, list):
            return [self.render_value(v, context) for v in value]
        if isinstance(value, dict):
            return {k: self.render_value(v, context) for k, v in value.items()}
        return value
