"""AI Utils — Typer CLI entry point."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="ai-utils",
    help="Local-first AI workflow platform.",
    no_args_is_help=True,
)
console = Console()

# ── Markdown formatting sub-app ─────────────────────────────────────────────
markdown_app = typer.Typer(help="Markdown formatting and compliance tools.", no_args_is_help=True)
app.add_typer(markdown_app, name="markdown")
# ── Markdown formatting commands ────────────────────────────────────────────

@markdown_app.command("format")
def format_markdown_cli(
    file: Annotated[str, typer.Argument(help="Path to markdown file or directory.")],
    in_place: Annotated[bool, typer.Option("--in-place", help="Overwrite files in place.")] = False,
    output_dir: Annotated[str | None, typer.Option("--output-dir", help="Directory for formatted output.")] = None,
    model: Annotated[str, typer.Option("--model", help="Model to use (default: qwen/qwen3.6-27b)")] = "qwen/qwen3.6-27b",
) -> None:
    """Format a markdown file or all .md files in a directory using LM Studio."""
    import os
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
    console.print(f"[green]✓ Markdown formatting complete for {len(files)} file(s).[/green]")

# ── Sub-apps ──────────────────────────────────────────────────────────────────

db_app = typer.Typer(help="Database management commands.", no_args_is_help=True)
ingest_app = typer.Typer(help="Asset ingestion workflow.", no_args_is_help=True)
img_intel_app = typer.Typer(help="Image intelligence workflow.", no_args_is_help=True)

app.add_typer(db_app, name="db")
app.add_typer(ingest_app, name="ingest")
app.add_typer(img_intel_app, name="image-intelligence")


# ── db commands ───────────────────────────────────────────────────────────────

@db_app.command("init")
def db_init() -> None:
    """Initialise the SQLite database (create tables if not present)."""
    from core.config import get_settings
    from drivers.sql.session import init_db

    settings = get_settings()
    console.print(f"[bold]Initialising database:[/bold] {settings.db_path}")
    init_db(settings.db_path)
    console.print("[green]✓ Database ready.[/green]")


# ── ingest commands ───────────────────────────────────────────────────────────

@ingest_app.command("run")
def ingest_run(
    source: Annotated[str, typer.Option("--source", "-s", help="Source folder to ingest.")],
    collection: Annotated[
        str, typer.Option("--collection", "-c", help="Collection name (e.g. sequoia-waste).")
    ],
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Show what would happen without copying.")
    ] = False,
) -> None:
    """Scan a source folder and ingest assets into the platform."""
    from core.config import get_settings
    from drivers.sql.session import init_db
    from workflows.langgraph.ingest.graph import run_ingest

    settings = get_settings()
    init_db(settings.db_path)

    mode = "[yellow]DRY RUN[/yellow]" if dry_run else "[green]LIVE[/green]"
    console.print(f"\n[bold]Ingestion workflow[/bold] ({mode})")
    console.print(f"  Source:     {source}")
    console.print(f"  Collection: {collection}")
    console.print(f"  Database:   {settings.db_path}\n")

    with console.status("Running ingestion workflow…"):
        state = run_ingest(source_dir=source, collection=collection, dry_run=dry_run)

    # ── Summary table ─────────────────────────────────────────────────────────
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
        console.print("\n[yellow]Dry run complete — no files were copied or registered.[/yellow]")
    else:
        console.print("\n[green]✓ Ingestion complete.[/green]")


# ── image-intelligence commands ───────────────────────────────────────────────

@img_intel_app.command("run")
def img_intel_run(
    collection: Annotated[
        str, typer.Option("--collection", "-c", help="Collection name to process.")
    ],
    concurrency: Annotated[
        int | None,
        typer.Option("--concurrency", help="Number of images to process in parallel."),
    ] = None,
    limit: Annotated[
        int | None,
        typer.Option("--limit", help="Process only the first N images (for smoke testing)."),
    ] = None,
) -> None:
    """Run the image intelligence pipeline on all images in a collection."""
    from core.config import get_settings
    from drivers.sql.session import init_db
    from workflows.langgraph.image_intelligence.graph import run_batch

    settings = get_settings()
    init_db(settings.db_path)

    workers = concurrency or settings.batch_concurrency
    console.print("\n[bold]Image Intelligence Pipeline[/bold]")
    console.print(f"  Collection:  {collection}")
    console.print(f"  Concurrency: {workers}")
    if limit:
        console.print(f"  Limit:       {limit} images")
    console.print()

    # Preflight: report Ollama availability through its harness contract.
    from harnesses.ollama import OllamaHarness
    try:
        ollama = OllamaHarness({"base_url": settings.ollama_api, "manage_server": False})
        status = ollama.status()
        model_names = status.metadata.get("models", []) if status.ok() else []
        if not any(settings.vision_model in m for m in model_names):
            console.print(
                f"[yellow]Warning: vision model '{settings.vision_model}' not found in Ollama. "
                f"Available: {model_names}[/yellow]"
            )
    except Exception as exc:
        console.print(
            f"[yellow]Warning: could not inspect Ollama at {settings.ollama_api}: {exc}[/yellow]"
        )

    with console.status("Processing images…"):
        results = run_batch(collection=collection, concurrency=workers, limit=limit)

    if not results:
        console.print("[yellow]No images found for this collection.[/yellow]")
        return

    succeeded = [r for r in results if r.get("status") == "success"]
    failed = [r for r in results if r.get("status") == "failed"]

    table = Table(title="Image Intelligence Summary", show_header=True)
    table.add_column("Metric", style="bold")
    table.add_column("Count", justify="right")
    table.add_row("Total processed", str(len(results)))
    table.add_row("Succeeded", f"[green]{len(succeeded)}[/green]")
    table.add_row("Failed", f"[red]{len(failed)}[/red]" if failed else "0")
    console.print(table)

    if failed:
        console.print("\n[red]Failed images:[/red]")
        for r in failed:
            console.print(f"  • {r.get('asset_id')} — {r.get('error')}")

    console.print(
        f"\n[green]✓ Done. Reports saved to: "
        f"{settings.outputs_root}/images/{collection}/[/green]"
    )


@img_intel_app.command("single")
def img_intel_single(
    image: Annotated[str, typer.Argument(help="Path to image file.")],
    collection: Annotated[
        str, typer.Option("--collection", "-c", help="Collection label.")
    ] = "default",
) -> None:
    """Run the image intelligence pipeline on a single image (no DB required)."""
    from core.config import get_settings
    from drivers.sql.session import init_db
    from workflows.langgraph.image_intelligence.graph import run_image_intelligence

    settings = get_settings()
    init_db(settings.db_path)

    console.print(f"\n[bold]Processing:[/bold] {image}\n")
    with console.status("Running…"):
        result = run_image_intelligence(image_path=image, collection=collection)

    out = result.get("output_path")
    if out:
        console.print(f"[green]✓ Report saved: {out}[/green]")
    else:
        console.print(f"[red]Failed: {result.get('error')}[/red]")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app()
