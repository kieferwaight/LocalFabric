"""Platform-wide configuration loaded from environment / .env file."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Ollama ────────────────────────────────────────────────────────────────
    ollama_api: str = "http://127.0.0.1:11434"
    vision_model: str = "llama3.2-vision"
    embed_model: str = "nomic-embed-text"

    # ── Storage ───────────────────────────────────────────────────────────────
    db_path: Path = Path("data/ai_utils.db")
    data_root: Path = Path("data")

    # ── Qdrant ────────────────────────────────────────────────────────────────
    qdrant_url: str = "http://localhost:6333"

    # ── Processing ────────────────────────────────────────────────────────────
    batch_concurrency: int = 4

    # ── Migration (from shared/config.py) ─────────────────────────────────────
    dry_run_default: bool = True
    confidence_review_threshold: float = 0.80
    collision_suffix_pattern: str = "__conflict_{n}"
    preserve_mtime: bool = True
    protected_inbox_subpaths: tuple[str, ...] = (
        "00_inbox/business",
        "00_inbox/misc",
        "00_inbox/personal",
        "00_inbox/resume",
        "00_inbox/resumes",
    )
    fully_excluded_prefixes: tuple[str, ...] = (
        "20_backups",
        "20_Backups",
    )
    ignored_dir_names: tuple[str, ...] = (
        ".git",
        "node_modules",
        "__pycache__",
    )
    ignored_file_names: tuple[str, ...] = (
        ".DS_Store",
    )

    # ── Derived paths (computed, not from env) ────────────────────────────────
    @property
    def inputs_root(self) -> Path:
        return self.data_root / "inputs"

    @property
    def outputs_root(self) -> Path:
        return self.data_root / "outputs"

    @property
    def manifests_root(self) -> Path:
        return self.data_root / "manifests"

    @field_validator("db_path", "data_root", mode="before")
    @classmethod
    def _coerce_path(cls, v: object) -> Path:
        return Path(v)  # type: ignore[arg-type]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the singleton Settings instance."""
    return Settings()
