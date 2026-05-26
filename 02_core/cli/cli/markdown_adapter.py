"""CLI adapter for the markdown-formatting workflow.

This adapter exposes ``localfabric markdown format <file_or_dir>``, which
drives the LangGraph markdown-format workflow. The raw-markdown runtime
that compiles and runs a prompt file lives in
[markdown_runtime_adapter.py](markdown_runtime_adapter.py) — a separate
single-domain adapter.
"""

from __future__ import annotations

import os
from typing import Annotated

import typer
from rich.console import Console

from adapters.cli.base import CliAdapter, CliCommand

console = Console()


class MarkdownFormatCommand(CliCommand):
    name = "format"
    help = "Format a markdown file or all .md files in a directory using LM Studio."

    @staticmethod
    def run(
        file: Annotated[str, typer.Argument(help="Path to markdown file or directory.")],
        in_place: Annotated[
            bool, typer.Option("--in-place", help="Overwrite files in place.")
        ] = False,
        output_dir: Annotated[
            str | None,
            typer.Option("--output-dir", help="Directory for formatted output."),
        ] = None,
        model: Annotated[
            str,
            typer.Option("--model", help="Model to use (default: qwen/qwen3.6-27b)"),
        ] = "qwen/qwen3.6-27b",
    ) -> None:
        from workflows.langgraph.markdown_format.graph import run_markdown_format_workflow

        if os.path.isdir(file):
            files = [
                os.path.join(file, f)
                for f in os.listdir(file)
                if f.endswith(".md") and os.path.isfile(os.path.join(file, f))
            ]
            if not files:
                console.print(f"[yellow]No markdown files found in directory: {file}[/yellow]")
                raise typer.Exit(1)
        else:
            files = [file]

        run_markdown_format_workflow(files, model=model, in_place=in_place, output_dir=output_dir)
        console.print(
            f"[green]✓ Markdown formatting complete for {len(files)} file(s).[/green]"
        )


class MarkdownCliAdapter(CliAdapter):
    domain = "markdown_format"
    typer_name = "markdown"
    typer_help = "Markdown formatting and compliance tools."
    commands = [MarkdownFormatCommand]


__all__ = ["MarkdownCliAdapter", "MarkdownFormatCommand"]
