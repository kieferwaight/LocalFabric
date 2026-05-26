"""``localfabric image-intelligence`` — image-intelligence workflow."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

console = Console()

image_intelligence_app = typer.Typer(
    help="Image intelligence workflow.",
    no_args_is_help=True,
)

_DEFAULT_DB_PATH_PARTS = ("workspace.db",)
_DEFAULT_OUTPUTS_PARTS = ("outputs",)
_DEFAULT_CONCURRENCY = 4
_DEFAULT_VISION_MODEL = "llama3.2-vision"


def _warn_if_vision_model_missing() -> None:
    """Preflight check: report Ollama vision-model availability."""
    from harnesses.ollama import OllamaHarness

    try:
        ollama = OllamaHarness({"manage_server": False})
        status = ollama.status()
        model_names = status.metadata.get("models", []) if status.ok() else []
        if not any(_DEFAULT_VISION_MODEL in m for m in model_names):
            console.print(
                f"[yellow]Warning: vision model '{_DEFAULT_VISION_MODEL}' not found in Ollama. "
                f"Available: {model_names}[/yellow]"
            )
    except Exception as exc:  # noqa: BLE001 - cosmetic preflight
        console.print(f"[yellow]Warning: could not inspect Ollama: {exc}[/yellow]")


@image_intelligence_app.command(
    "run", help="Run the image intelligence pipeline on all images in a collection."
)
def image_intelligence_run(
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
    from core.environment import data
    from drivers.sql.session import init_db
    from workflows.langgraph.image_intelligence.graph import run_batch

    init_db(data(*_DEFAULT_DB_PATH_PARTS))

    workers = concurrency or _DEFAULT_CONCURRENCY
    console.print("\n[bold]Image Intelligence Pipeline[/bold]")
    console.print(f"  Collection:  {collection}")
    console.print(f"  Concurrency: {workers}")
    if limit:
        console.print(f"  Limit:       {limit} images")
    console.print()

    _warn_if_vision_model_missing()

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

    outputs_root = data(*_DEFAULT_OUTPUTS_PARTS)
    console.print(
        f"\n[green]✓ Done. Reports saved to: "
        f"{outputs_root}/images/{collection}/[/green]"
    )


@image_intelligence_app.command(
    "single",
    help="Run the image intelligence pipeline on a single image (no DB required).",
)
def image_intelligence_single(
    image: Annotated[str, typer.Argument(help="Path to image file.")],
    collection: Annotated[
        str, typer.Option("--collection", "-c", help="Collection label.")
    ] = "default",
) -> None:
    from core.environment import data
    from drivers.sql.session import init_db
    from workflows.langgraph.image_intelligence.graph import run_image_intelligence

    init_db(data(*_DEFAULT_DB_PATH_PARTS))

    console.print(f"\n[bold]Processing:[/bold] {image}\n")
    with console.status("Running…"):
        result = run_image_intelligence(image_path=image, collection=collection)

    out = result.get("output_path")
    if out:
        console.print(f"[green]✓ Report saved: {out}[/green]")
    else:
        console.print(f"[red]Failed: {result.get('error')}[/red]")
