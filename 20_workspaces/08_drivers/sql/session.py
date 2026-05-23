"""SQLAlchemy engine factory and session helpers."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Connection, create_engine, text
from sqlalchemy.engine import Engine

from drivers.sql.schema import metadata

_engine: Engine | None = None


def _get_engine(db_path: Path) -> Engine:
    global _engine
    if _engine is None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
        )
    return _engine


def init_db(db_path: Path) -> None:
    """Create all tables if they don't already exist."""
    engine = _get_engine(db_path)
    metadata.create_all(engine)
    # Enable WAL mode for better concurrent read performance
    with engine.connect() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL"))
        conn.execute(text("PRAGMA foreign_keys=ON"))
        conn.commit()


@contextmanager
def get_connection(db_path: Path) -> Generator[Connection, None, None]:
    """Yield a SQLAlchemy connection; commit on success, rollback on error."""
    engine = _get_engine(db_path)
    with engine.begin() as conn:
        yield conn


def reset_engine() -> None:
    """Dispose the engine (used in tests to start fresh)."""
    global _engine
    if _engine is not None:
        _engine.dispose()
        _engine = None
