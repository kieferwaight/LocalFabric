"""Markdown source → YAML runtime definition dict.

Pure function: takes a string of markdown and returns a definition dict that
`core.runtimes.yaml.src.Runtime.import_yaml_raw([dict])` accepts. No I/O. No
runtime side effects. Identical input produces identical output.
"""

from __future__ import annotations

import logging
from typing import Any

from . import fences as _fences
from . import frontmatter as _frontmatter

logger = logging.getLogger("core.runtimes.markdown")


class MarkdownCompileError(ValueError):
    """Raised for any malformed markdown source the compiler refuses to accept."""


# Markdown fence-info language tokens → dispatcher language names.
# Tokens not listed here are skipped (with a warning) in step 1.
_LANGUAGE_MAP: dict[str, str] = {
    "bash": "bash",
    "sh": "sh",
    "python": "python",
    "py": "python",
    "js": "js",
    "javascript": "js",
    "node": "js",
}

# Frontmatter keys passed through to the definition dict verbatim. Anything
# else (e.g. `title`) is intentionally NOT forwarded — `title` is markdown
# author metadata that the YAML runtime would treat as a definition field.
# We include it explicitly because the YAML schema supports it.
_FORWARDED_KEYS: tuple[str, ...] = (
    "id",
    "title",
    "description",
    "tags",
    "extends",
    "mixins",
    "modules",
    "inputs",
    "variables",
)

#: Magic marker key embedded in the compiled definition for provider-style
#: files. ``MarkdownHarness.execute`` reads it to choose between the YAML
#: runtime path and the provider dispatch path. Underscore-prefixed so the
#: YAML runtime's schema validator (which is strict about top-level keys)
#: never sees it — provider files don't reach the runtime in the first place.
PROVIDER_MARKER_KEY: str = "_markdown_provider"


def compile_text(source: str, *, source_path: str = "<string>") -> dict[str, Any]:
    """Compile markdown text → in-memory YAML runtime definition dict.

    Two shapes are supported:

    * **Fence-style** (default): frontmatter declares a workflow definition
      and fenced code blocks in the body become entries on its ``run`` list.
      Output is consumed by ``core.runtimes.yaml.src.Runtime.import_yaml_raw``.

    * **Provider-style**: when frontmatter declares ``provider:`` the body is
      treated as a single Jinja-renderable prompt and stored under the
      ``_markdown_provider`` key. The markdown harness routes these files
      through ``core.runtimes.markdown.providers`` instead of the YAML runtime.
    """
    try:
        fm = _frontmatter.parse(source, source_path=source_path)
    except _frontmatter._FrontmatterError as exc:
        raise MarkdownCompileError(str(exc)) from exc

    if "provider" in fm.metadata:
        return _compile_provider_style(fm, source_path=source_path)

    try:
        fence_blocks = _fences.parse(
            fm.body, body_start_line=fm.body_start_line, source_path=source_path
        )
    except _fences._FenceError as exc:
        raise MarkdownCompileError(str(exc)) from exc

    definition: dict[str, Any] = {}
    for key in _FORWARDED_KEYS:
        if key in fm.metadata:
            definition[key] = fm.metadata[key]

    # Title fallback: explicit frontmatter wins; else the first H1 in body;
    # else nothing — the YAML runtime defaults `title` to "" anyway.
    if "title" not in definition:
        h1 = _first_h1(fm.body)
        if h1:
            definition["title"] = h1

    # Author-declared `variables.body` wins over the implicit bind.
    variables = dict(definition.get("variables") or {})
    if "body" not in variables:
        variables["body"] = fm.body
    if variables:
        definition["variables"] = variables

    run, seen_ids = _compile_run_blocks(fence_blocks, source_path)
    definition["run"] = run

    # Validate unique block ids include skipped blocks per spec ("skipped
    # blocks' ids still count toward uniqueness"). _compile_run_blocks
    # tracks them.
    _ = seen_ids
    return definition


def _compile_provider_style(
    fm: _frontmatter.Frontmatter, *, source_path: str
) -> dict[str, Any]:
    """Build a provider-style definition dict.

    The body becomes the prompt template; ``inputs``, ``description``, and
    ``title`` are preserved for documentation. The YAML runtime never sees
    this dict — the markdown harness reads ``_markdown_provider`` and
    dispatches via ``core.runtimes.markdown.providers`` directly.
    """
    metadata = fm.metadata

    provider = metadata.get("provider")
    if not isinstance(provider, str) or not provider.strip():
        raise MarkdownCompileError(
            f"{source_path}: frontmatter 'provider' must be a non-empty string."
        )

    model = metadata.get("model")
    if model is not None and (not isinstance(model, str) or not model.strip()):
        raise MarkdownCompileError(
            f"{source_path}: frontmatter 'model' must be a non-empty string when set."
        )

    system = metadata.get("system")
    if system is not None and not isinstance(system, str):
        raise MarkdownCompileError(
            f"{source_path}: frontmatter 'system' must be a string when set."
        )

    stream = metadata.get("stream")
    if stream is not None and not isinstance(stream, bool):
        raise MarkdownCompileError(
            f"{source_path}: frontmatter 'stream' must be a boolean when set."
        )

    max_tokens = metadata.get("max_tokens")
    if max_tokens is not None and (
        isinstance(max_tokens, bool) or not isinstance(max_tokens, int)
    ):
        raise MarkdownCompileError(
            f"{source_path}: frontmatter 'max_tokens' must be an integer when set."
        )

    temperature = metadata.get("temperature")
    if temperature is not None and not isinstance(temperature, (int, float)):
        raise MarkdownCompileError(
            f"{source_path}: frontmatter 'temperature' must be a number when set."
        )

    # Reject fence-style keys that would silently no-op under provider mode.
    for stray in ("extends", "mixins", "modules", "variables"):
        if stray in metadata:
            raise MarkdownCompileError(
                f"{source_path}: frontmatter key {stray!r} is not supported in "
                "provider-style markdown (provider: is set)."
            )

    raw_id = metadata["id"]  # frontmatter parser guaranteed presence
    description = metadata.get("description")
    title = metadata.get("title")
    if title is None:
        title = _first_h1(fm.body) or ""
    inputs = metadata.get("inputs")

    provider_config = {
        "provider": provider.strip(),
        "prompt_template": fm.body,
        "source_path": source_path,
    }
    for key in ("model", "system", "stream", "max_tokens", "temperature"):
        value = metadata.get(key)
        if value is not None:
            provider_config[key] = value

    definition: dict[str, Any] = {
        "id": raw_id,
        "title": title,
        PROVIDER_MARKER_KEY: provider_config,
    }
    if description is not None:
        definition["description"] = description
    if inputs is not None:
        definition["inputs"] = inputs
    return definition


def _compile_run_blocks(
    fence_blocks: list[_fences.Fence], source_path: str
) -> tuple[list[dict[str, Any]], set[str]]:
    run: list[dict[str, Any]] = []
    seen_ids: dict[str, int] = {}

    for fence in fence_blocks:
        block_id = fence.attributes.get("id")
        if block_id is not None:
            if not isinstance(block_id, str) or not block_id.strip():
                raise MarkdownCompileError(
                    f"{source_path}:{fence.start_line}: fence 'id' must be a non-empty string."
                )
            if block_id in seen_ids:
                raise MarkdownCompileError(
                    f"{source_path}:{fence.start_line}: duplicate block id {block_id!r}; "
                    f"first seen on line {seen_ids[block_id]}."
                )
            seen_ids[block_id] = fence.start_line

        if fence.attributes.get("skip") is True:
            continue

        if not fence.language:
            # Bare fence without a language token. Documentation only.
            continue

        dispatcher_lang = _LANGUAGE_MAP.get(fence.language)
        if dispatcher_lang is None:
            logger.warning(
                "%s:%d: skipping fence with unrecognized language %r",
                source_path,
                fence.start_line,
                fence.language,
            )
            continue

        block: dict[str, Any] = {dispatcher_lang: fence.content}

        # Forward-compat: preserve unknown attributes on the block as metadata
        # so step 2/3 can read them without breaking step 1 authors.
        metadata = {
            k: v
            for k, v in fence.attributes.items()
            if k not in {"id", "skip"}
        }
        if metadata:
            block["_markdown_attributes"] = metadata

        run.append(block)

    return run, set(seen_ids)


def _first_h1(body: str) -> str | None:
    for raw in body.splitlines():
        stripped = raw.lstrip()
        if stripped.startswith("# ") and not stripped.startswith("##"):
            return stripped[2:].strip() or None
    return None
