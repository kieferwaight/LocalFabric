"""Local research workflow: acquire text, then summarize through a local harness.

The public entry point is ``local_research_scaffold(topic_or_url)``. It fetches
readable text via ``lib.browser.fetch_text``, selects an available Ollama model
(preferring ``qwen2.5:7b``), loads the prompt template from
``12_prompts/tasks.research-summary.md``, and invokes the model through
``OllamaHarness``. Stateful pieces — model selection and harness construction —
happen inside each call; this is intentional (keeps the function simple and
avoids shared state). Pass an explicit ``harness`` argument to inject a fake
in tests or to reuse a pre-configured harness across multiple calls.

Returns a plain-text summary string. Graceful fallbacks are built in: if Ollama
is unreachable, the cleaned raw extract is returned instead of raising.
"""

from __future__ import annotations

import os
from pathlib import Path

from core.runtimes.markdown.frontmatter import parse as parse_frontmatter
from harnesses.ollama import OllamaHarness
from lib.browser.fetch_text import fetch_readable_text


_PROMPT_PATH = Path(__file__).resolve().parents[2] / "12_prompts" / "tasks.research-summary.md"
_MODEL_PREFERENCE = ("qwen2.5:7b", "qwen2.5", "llama3", "llama3.2", "llama3.1")


def _build_harness() -> OllamaHarness:
    return OllamaHarness(
        {
            "base_url": os.environ.get("OLLAMA_API", OllamaHarness.DEFAULT_BASE_URL),
            "manage_server": False,
        }
    )


def _pick_ollama_model(harness: OllamaHarness | None = None) -> str | None:
    """Return the first preferred local model advertised by Ollama."""
    executor = harness or _build_harness()
    status = executor.status()
    names = status.metadata.get("models", []) if status.ok() else []
    for preference in _MODEL_PREFERENCE:
        for name in names:
            if name.startswith(preference):
                return name
    return names[0] if names else None


def local_research_scaffold(topic_or_url: str, harness: OllamaHarness | None = None) -> str:
    """Fetch readable content and summarize it through the local Ollama harness."""
    try:
        clean_text, source_label, target = fetch_readable_text(topic_or_url)
    except Exception as exc:
        return f"Local Scraper Failed to fetch data: {exc}"

    if not clean_text:
        return f"Local Scraper returned no readable text from {source_label}: {target}"

    executor = harness or _build_harness()
    model = _pick_ollama_model(executor)
    if model is None:
        return (
            f"Ollama unavailable - returning cleaned raw extract ({len(clean_text)} chars):\n\n"
            f"{clean_text}"
        )

    prompt_body = parse_frontmatter(
        _PROMPT_PATH.read_text(encoding="utf-8"), source_path=str(_PROMPT_PATH)
    ).body
    prompt = prompt_body.replace("{{ source_text }}", clean_text)
    try:
        response = executor.invoke(
            {"model": model, "prompt": prompt, "options": {"temperature": 0.2}}
        )
        summary = response.get("message", {}).get("content", response.get("response", ""))
        return f"[model: {model}]\n\n{summary}"
    except Exception as exc:
        return (
            f"Ollama local processing failed with model {model}: {exc}. "
            f"Raw extracted text snippet:\n{clean_text[:500]}"
        )
