"""``localfabric db`` — database management commands."""

from __future__ import annotations

import typer
from rich.console import Console

console = Console()

db_app = typer.Typer(help="Database management commands.", no_args_is_help=True)

_DEFAULT_DB_PATH_PARTS = ("workspace.db",)


@db_app.command("init", help="Initialise the SQLite database (create tables if not present).")
def db_init() -> None:
    from core.environment import data
    from drivers.sql.session import init_db

    db_path = data(*_DEFAULT_DB_PATH_PARTS)
    console.print(f"[bold]Initialising database:[/bold] {db_path}")
    init_db(db_path)
    console.print("[green]✓ Database ready.[/green]")
