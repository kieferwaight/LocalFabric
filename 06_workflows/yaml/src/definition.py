"""Definition and documentation metadata dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class InputConstraint:
    type: str = "string"
    required: bool = False
    default: Any = None
    description: str = ""

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> InputConstraint:
        allowed = {"string", "number", "boolean", "array", "object"}
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
class BlockDocumentation:
    title: str = ""
    description: str = ""

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> BlockDocumentation:
        if not isinstance(raw, dict):
            raise ValueError("Lifecycle documentation entries must be mappings.")
        return cls(
            title=str(raw.get("title", "")),
            description=str(raw.get("description", "")),
        )


@dataclass
class DefinitionDocumentation:
    variables: dict[str, str] = field(default_factory=dict)
    run: list[BlockDocumentation] = field(default_factory=list)
    teardown: list[BlockDocumentation] = field(default_factory=list)

    @classmethod
    def from_dict(
        cls,
        raw: dict[str, Any],
        variables: dict[str, Any],
        run: list[dict[str, Any]],
        teardown: list[dict[str, Any]],
    ) -> DefinitionDocumentation:
        if not isinstance(raw, dict):
            raise ValueError("Definition 'docs' must be a mapping.")
        variables_raw = raw.get("variables") or {}
        if not isinstance(variables_raw, dict):
            raise ValueError("Definition 'docs.variables' must be a mapping.")
        unknown = sorted(set(variables_raw) - set(variables))
        if unknown:
            raise ValueError(f"Documentation references unknown local variables: {unknown!r}.")
        variable_docs = {str(key): str(value) for key, value in variables_raw.items()}
        run_docs = _parse_block_docs(raw.get("run"), "run", len(run))
        teardown_docs = _parse_block_docs(raw.get("teardown"), "teardown", len(teardown))
        return cls(variables=variable_docs, run=run_docs, teardown=teardown_docs)


def _parse_block_docs(raw: Any, name: str, block_count: int) -> list[BlockDocumentation]:
    items = raw or []
    if not isinstance(items, list):
        raise ValueError(f"Definition 'docs.{name}' must be a list.")
    if len(items) > block_count:
        raise ValueError(f"Definition 'docs.{name}' has more entries than local {name} blocks.")
    return [BlockDocumentation.from_dict(item) for item in items]


@dataclass
class TemplateBlock:
    engine: str = "jinja"
    output: str = "markdown"
    body: str = ""

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> TemplateBlock:
        if not isinstance(raw, dict):
            raise ValueError("Definition 'template' must be a mapping.")
        allowed_engines = {"jinja"}
        allowed_outputs = {"markdown", "text"}
        engine = str(raw.get("engine", "jinja"))
        output = str(raw.get("output", "markdown"))
        if engine not in allowed_engines:
            raise ValueError(f"Unsupported template engine: {engine!r}")
        if output not in allowed_outputs:
            raise ValueError(f"Unsupported template output: {output!r}")
        if "body" not in raw:
            raise ValueError("Definition 'template' requires a 'body' field.")
        body = raw["body"]
        if not isinstance(body, str):
            raise ValueError("Definition 'template.body' must be a string.")
        return cls(engine=engine, output=output, body=body)


@dataclass
class Definition:
    id: str
    title: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)
    extends: str | None = None
    mixins: list[str] = field(default_factory=list)
    modules: list[str] = field(default_factory=list)
    run: list[dict[str, Any]] = field(default_factory=list)
    variables: dict[str, Any] = field(default_factory=dict)
    inputs: dict[str, InputConstraint] = field(default_factory=dict)
    teardown: list[dict[str, Any]] = field(default_factory=list)
    docs: DefinitionDocumentation = field(default_factory=DefinitionDocumentation)
    template: TemplateBlock | None = None

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Definition:
        if "id" not in raw:
            raise ValueError("Definition is missing required 'id' field.")
        inputs_raw = raw.get("inputs") or {}
        inputs = {k: InputConstraint.from_dict(v or {}) for k, v in inputs_raw.items()}
        modules = raw.get("modules") or []
        if not isinstance(modules, list) or not all(isinstance(path, str) for path in modules):
            raise ValueError("Definition 'modules' must be a list of YAML file paths.")
        tags = raw.get("tags") or []
        if not isinstance(tags, list) or not all(isinstance(tag, str) and tag for tag in tags):
            raise ValueError("Definition 'tags' must be a list of non-empty strings.")
        run = list(raw.get("run") or [])
        variables = dict(raw.get("variables") or {})
        teardown = list(raw.get("teardown") or [])
        docs = DefinitionDocumentation.from_dict(raw.get("docs") or {}, variables, run, teardown)
        template_raw = raw.get("template")
        template = TemplateBlock.from_dict(template_raw) if template_raw is not None else None
        return cls(
            id=str(raw["id"]),
            title=str(raw.get("title", "")),
            description=str(raw.get("description", "")),
            tags=list(tags),
            extends=raw.get("extends"),
            mixins=list(raw.get("mixins") or []),
            modules=list(modules),
            run=run,
            variables=variables,
            inputs=inputs,
            teardown=teardown,
            docs=docs,
            template=template,
        )
