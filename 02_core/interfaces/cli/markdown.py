"""``localfabric markdown format`` — markdown-formatting workflow.

The raw markdown-runtime entry (``localfabric-md``) is in
``markdown_runtime.py`` — it has its own argv shape and does not
register a Typer command.
"""

from __future__ import annotations

import os
from typing import Annotated

import typer
from rich.console import Console

console = Console()

markdown_app = typer.Typer(
    help="Markdown formatting and compliance tools.",
    no_args_is_help=True,
)


@markdown_app.command(
    "format",
    help="Format a markdown file or all .md files in a directory using LM Studio.",
)
def markdown_format(
    file: Annotated[str, typer.Argument(help="Path to markdown file or directory.")],
    in_place: Annotated[bool, typer.Option("--in-place", help="Overwrite files in place.")] = False,
    output_dir: Annotated[
        str | None,
        typer.Option("--output-dir", help="Directory for formatted output."),
    ] = None,
    model: Annotated[
        str,
        typer.Option("--model", help="Model to use (default: qwen/qwen3.6-27b)"),
    ] = "qwen/qwen3.6-27b",
) -> None:
    from core.runtimes.langgraph.markdown_format.graph import run_markdown_format_workflow

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
    console.print(f"[green]✓ Markdown formatting complete for {len(files)} file(s).[/green]")
