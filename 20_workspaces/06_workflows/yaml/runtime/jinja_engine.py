"""Multi-pass Jinja2 renderer used to expand variables and run blocks."""

from __future__ import annotations

from typing import Any

from jinja2 import Environment, StrictUndefined


class JinjaEngine:
    MAX_PASSES = 10

    def __init__(self, env: Environment | None = None) -> None:
        self.env = env or Environment(
            autoescape=False,
            keep_trailing_newline=True,
            undefined=StrictUndefined,
        )

    def render(self, source: str, context: dict[str, Any]) -> str:
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

    def render_value(self, value: Any, context: dict[str, Any]) -> Any:
        if isinstance(value, str):
            return self.render(value, context)
        if isinstance(value, list):
            return [self.render_value(v, context) for v in value]
        if isinstance(value, dict):
            return {k: self.render_value(v, context) for k, v in value.items()}
        return value

    def evaluate(self, expression: Any, context: dict[str, Any]) -> Any:
        """Evaluate a native Jinja expression for structured workflow operations."""
        if not isinstance(expression, str):
            return expression
        return self.env.compile_expression(expression)(**context)

    def render_template(self, source: str, context: dict[str, Any]) -> str:
        """Render an authored template once, preserving template syntax in data values."""
        return self.env.from_string(source).render(**context)
