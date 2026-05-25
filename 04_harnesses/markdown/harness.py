"""Public MarkdownHarness — compile-and-dispatch shim over the YAML runtime."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from workflows.yaml.src import Runtime

from .compiler import MarkdownCompileError, compile_text

logger = logging.getLogger("harnesses.markdown")


class MarkdownHarness:
    """Compile `.md` files into runtime `Definition`s and execute them.

    The harness is a thin lifecycle shim. It owns markdown ingest, registry
    insertion, and dispatch to the YAML runtime. All script execution,
    inheritance, scope frames, and the IPC state bridge belong to the YAML
    runtime — this class never duplicates them.
    """

    def __init__(self, runtime: Runtime | None = None) -> None:
        self.runtime: Runtime = runtime if runtime is not None else Runtime()

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
    ) -> dict[str, Any]:
        definition_id = self.register(path)
        return self.runtime.execute(definition_id, dict(arguments or {}))
