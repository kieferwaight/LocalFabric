"""CLI adapter for database management."""

from __future__ import annotations

from rich.console import Console

from adapters.cli.base import CliAdapter, CliCommand

console = Console()

_DEFAULT_DB_PATH_PARTS = ("workspace.db",)


class DbInitCommand(CliCommand):
    name = "init"
    help = "Initialise the SQLite database (create tables if not present)."

    @staticmethod
    def run() -> None:
        from core.paths import data
        from drivers.sql.session import init_db

        db_path = data(*_DEFAULT_DB_PATH_PARTS)
        console.print(f"[bold]Initialising database:[/bold] {db_path}")
        init_db(db_path)
        console.print("[green]✓ Database ready.[/green]")


class DbCliAdapter(CliAdapter):
    domain = "db"
    typer_name = "db"
    typer_help = "Database management commands."
    commands = [DbInitCommand]


__all__ = ["DbCliAdapter", "DbInitCommand"]
