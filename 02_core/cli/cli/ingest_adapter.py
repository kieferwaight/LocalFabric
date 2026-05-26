"""CLI adapter for the asset-ingestion workflow."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from adapters.cli.base import CliAdapter, CliCommand

console = Console()

_DEFAULT_DB_PATH_PARTS = ("workspace.db",)


class IngestRunCommand(CliCommand):
    name = "run"
    help = "Scan a source folder and ingest assets into the platform."

    @staticmethod
    def run(
        source: Annotated[str, typer.Option("--source", "-s", help="Source folder to ingest.")],
        collection: Annotated[
            str, typer.Option("--collection", "-c", help="Collection name (e.g. sequoia-waste).")
        ],
        dry_run: Annotated[
            bool, typer.Option("--dry-run", help="Show what would happen without copying.")
        ] = False,
    ) -> None:
        from core.environment import data
        from drivers.sql.session import init_db
        from workflows.langgraph.ingest.graph import run_ingest

        db_path = data(*_DEFAULT_DB_PATH_PARTS)
        init_db(db_path)

        mode = "[yellow]DRY RUN[/yellow]" if dry_run else "[green]LIVE[/green]"
        console.print(f"\n[bold]Ingestion workflow[/bold] ({mode})")
        console.print(f"  Source:     {source}")
        console.print(f"  Collection: {collection}")
        console.print(f"  Database:   {db_path}\n")

        with console.status("Running ingestion workflow…"):
            state = run_ingest(source_dir=source, collection=collection, dry_run=dry_run)

        copied = state.get("copied_files", [])
        images = [f for f in copied if f.get("media_class") == "image"]
        docs = [f for f in copied if f.get("media_class") == "document"]
        duplicates = [f for f in copied if f.get("is_duplicate")]
        errors = state.get("errors", [])

        table = Table(title="Ingestion Summary", show_header=True)
        table.add_column("Metric", style="bold")
        table.add_column("Count", justify="right")
        table.add_row("Total scanned", str(len(state.get("scanned_files", []))))
        table.add_row("Images", str(len(images)))
        table.add_row("Documents", str(len(docs)))
        table.add_row(
            "Other",
            str(len([f for f in copied if f.get("media_class") == "unknown"])),
        )
        table.add_row("Duplicates flagged", str(len(duplicates)))
        table.add_row(
            "Registered (new)",
            str(state.get("registered_count", 0)) if not dry_run else "—",
        )
        table.add_row("Errors", str(len(errors)))
        console.print(table)

        if errors:
            console.print("\n[red]Errors:[/red]")
            for e in errors:
                console.print(f"  • {e}")

        if dry_run:
            console.print(
                "\n[yellow]Dry run complete — no files were copied or registered.[/yellow]"
            )
        else:
            console.print("\n[green]✓ Ingestion complete.[/green]")


class IngestCliAdapter(CliAdapter):
    domain = "ingest"
    typer_name = "ingest"
    typer_help = "Asset ingestion workflow."
    commands = [IngestRunCommand]


__all__ = ["IngestCliAdapter", "IngestRunCommand"]
