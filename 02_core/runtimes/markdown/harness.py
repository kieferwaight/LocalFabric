"""Public MarkdownHarness — compile-and-dispatch shim over the YAML runtime."""

from __future__ import annotations

import logging
import sys
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any, TextIO

from core.runtimes.yaml.src import Runtime
from core.runtimes.yaml.src.jinja_engine import JinjaEngine

from .compiler import PROVIDER_MARKER_KEY, MarkdownCompileError, compile_text
from .providers import (
    MarkdownProvider,
    ProviderError,
    ProviderResult,
    get_provider,
)

logger = logging.getLogger("core.runtimes.markdown")


class MarkdownHarness:
    """Compile `.md` files into runtime `Definition`s and execute them.

    The harness is a thin lifecycle shim. It owns markdown ingest, registry
    insertion, and dispatch to the YAML runtime. All script execution,
    inheritance, scope frames, and the IPC state bridge belong to the YAML
    runtime — this class never duplicates them.

    For ``provider:`` markdown files the harness routes execution through
    ``core.runtimes.markdown.providers`` instead of the YAML runtime: the body
    is treated as a Jinja-renderable prompt template, the declared inputs
    are coerced and rendered into it, and the resulting prompt is sent to
    the provider harness (e.g. ``ClaudeHarness``).
    """

    def __init__(
        self,
        runtime: Runtime | None = None,
        *,
        provider_overrides: Mapping[str, MarkdownProvider] | None = None,
        stdout: TextIO | None = None,
    ) -> None:
        self.runtime: Runtime = runtime if runtime is not None else Runtime()
        self._provider_overrides: dict[str, MarkdownProvider] = (
            dict(provider_overrides) if provider_overrides else {}
        )
        # Standalone Jinja engine for provider-style files. The YAML
        # runtime's engine works on its own scope objects; provider-style
        # files render once with a plain dict context, which is simpler.
        self._jinja = JinjaEngine()
        self._stdout: TextIO = stdout if stdout is not None else sys.stdout

    # ------------------------------------------------------------------ pure
    def compile_text(self, source: str, *, source_path: str = "<string>") -> dict[str, Any]:
        return compile_text(source, source_path=source_path)

    def compile_file(self, path: str | Path) -> dict[str, Any]:
        resolved = Path(path)
        text = resolved.read_text(encoding="utf-8")
        return self.compile_text(text, source_path=str(resolved))

    # ----------------------------------------------------------------- ingest
    def register(self, path: str | Path) -> str:
        definition = self.compile_file(path)
        if PROVIDER_MARKER_KEY in definition:
            # Provider-style files do not enter the YAML runtime registry —
            # they have no `run:` list and the runtime's schema would reject
            # them. Calling `register` on a provider file is still a useful
            # ergonomic check (it validates compilation), so we accept it
            # and return the id without touching the runtime.
            return str(definition["id"])
        self.runtime.import_yaml_raw([definition])
        return str(definition["id"])

    def register_dir(self, path: str | Path, *, recursive: bool = True) -> list[str]:
        root = Path(path)
        if not root.is_dir():
            raise NotADirectoryError(f"register_dir requires a directory: {root}")
        pattern = "**/*.md" if recursive else "*.md"
        registered: list[str] = []
        for file in sorted(root.glob(pattern)):
            try:
                registered.append(self.register(file))
            except MarkdownCompileError as exc:
                logger.warning("Skipping %s: %s", file, exc)
        return registered

    # ----------------------------------------------------------------- execute
    def execute(
        self,
        path: str | Path,
        arguments: dict[str, Any] | None = None,
    ) -> dict[str, Any] | ProviderResult | Iterator[str]:
        """Execute the markdown file at ``path``.

        Fence-style files dispatch through the YAML runtime and return the
        final scope dict (existing behavior). Provider-style files (any
        file whose frontmatter declares ``provider:``) dispatch through the
        configured ``MarkdownProvider`` and return a ``ProviderResult`` —
        or an iterator of text chunks when the file or harness opts into
        streaming.
        """
        definition = self.compile_file(path)
        if PROVIDER_MARKER_KEY in definition:
            return self._execute_provider(definition, dict(arguments or {}))
        return self._execute_via_runtime(definition, dict(arguments or {}))

    # --------------------------------------------------------- runtime path
    def _execute_via_runtime(
        self, definition: dict[str, Any], arguments: dict[str, Any]
    ) -> dict[str, Any]:
        self.runtime.import_yaml_raw([definition])
        return self.runtime.execute(str(definition["id"]), arguments)

    # -------------------------------------------------------- provider path
    def _execute_provider(
        self, definition: dict[str, Any], arguments: dict[str, Any]
    ) -> ProviderResult | Iterator[str]:
        config = definition[PROVIDER_MARKER_KEY]
        provider_name = config["provider"]
        provider = get_provider(provider_name, overrides=self._provider_overrides)

        prompt = self._render_prompt(
            config["prompt_template"],
            inputs=definition.get("inputs") or {},
            arguments=arguments,
            source_path=config["source_path"],
        )

        stream_requested = bool(config.get("stream", False))
        kwargs: dict[str, Any] = {
            "model": config.get("model"),
            "system": config.get("system"),
            "stream": stream_requested,
        }
        if "max_tokens" in config:
            kwargs["max_tokens"] = config["max_tokens"]
        if "temperature" in config:
            kwargs["temperature"] = config["temperature"]

        try:
            result = provider.run(prompt, **kwargs)
        except ProviderError:
            raise
        except Exception as exc:  # noqa: BLE001 — re-wrap any unexpected SDK error
            raise ProviderError(
                f"{provider_name} provider raised an unexpected error: {exc}"
            ) from exc

        if stream_requested:
            return self._stream_to_stdout(result)
        assert isinstance(result, ProviderResult)
        return result

    def _stream_to_stdout(self, chunks: ProviderResult | Iterator[str]) -> Iterator[str]:
        """Yield streaming chunks while echoing them to stdout in real time."""
        if isinstance(chunks, ProviderResult):
            # A provider that doesn't actually stream still goes through here
            # if the file requested streaming; print once and re-yield.
            self._stdout.write(chunks.text)
            self._stdout.flush()
            yield chunks.text
            return
        for chunk in chunks:
            self._stdout.write(chunk)
            self._stdout.flush()
            yield chunk

    def _render_prompt(
        self,
        template: str,
        *,
        inputs: Mapping[str, Any],
        arguments: Mapping[str, Any],
        source_path: str,
    ) -> str:
        """Coerce/validate inputs, then render the body via Jinja."""
        context = self._coerce_inputs(inputs, arguments, source_path=source_path)
        return self._jinja.render_template(template, context)

    @staticmethod
    def _coerce_inputs(
        inputs: Mapping[str, Any],
        arguments: Mapping[str, Any],
        *,
        source_path: str,
    ) -> dict[str, Any]:
        from core.runtimes.yaml.src.runtime import coerce_type

        rendered: dict[str, Any] = dict(arguments)
        for name, raw_constraint in (inputs or {}).items():
            if not isinstance(raw_constraint, dict):
                continue
            expected_type = str(raw_constraint.get("type", "string"))
            required = bool(raw_constraint.get("required", False))
            default = raw_constraint.get("default")
            value = arguments.get(name)
            if value is None:
                if default is not None:
                    value = default
                elif required:
                    raise ValueError(
                        f"Missing required input {name!r} (type={expected_type}) for {source_path}."
                    )
                else:
                    rendered[name] = None
                    continue
            rendered[name] = coerce_type(value, expected_type)
        return rendered
