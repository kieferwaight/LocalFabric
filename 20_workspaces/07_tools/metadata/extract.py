from __future__ import annotations

from pathlib import Path


def infer_source_guess(rel_path: Path) -> str:
    parts = [p.lower() for p in rel_path.parts]
    for source in ("gemini", "openai", "perplexity", "undermind", "manual", "scraped", "uploads"):
        if source in parts:
            return source
    return "unknown"


def infer_doc_type(name: str) -> str:
    n = name.lower()
    if "report" in n:
        return "report"
    if "prompt" in n:
        return "prompt"
    if "spec" in n or "specification" in n:
        return "specification"
    if "draft" in n:
        return "draft"
    return "note"
