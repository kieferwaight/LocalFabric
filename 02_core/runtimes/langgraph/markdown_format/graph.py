"""Markdown formatting workflow orchestration."""

from __future__ import annotations

from pathlib import Path

from drivers.file import write_text_artifact
from core.runtimes.langgraph.markdown_format import nodes


def run_markdown_format_workflow(
    files: list[str],
    model: str = "qwen/qwen3.6-27b",
    in_place: bool = False,
    output_dir: str | None = None,
) -> None:
    """Format Markdown files and persist the resulting text through a driver."""
    for file_path in files:
        formatted = nodes.format_markdown_with_lmstudio(file_path, model=model)
        source = Path(file_path)
        destination = source if in_place else Path(output_dir or "formatted_markdown") / source.name
        write_text_artifact(destination, formatted)
