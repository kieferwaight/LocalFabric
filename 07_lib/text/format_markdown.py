"""Markdown formatting via a local LM Studio harness.

Reads a markdown file, applies the formatting prompt from ``12_prompts/text.markdown.format.task.md``
through an LM Studio harness, and returns the formatted content string. The harness is
constructed internally by default; pass an ``executor`` to inject a fake in tests.

Stateful pieces: LMStudioHarness construction and the prompt template load both happen
inside ``format_markdown_with_lmstudio`` on each call. The ``executor`` parameter makes
both substitutable without touching the default call path.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from core.runtimes.markdown.frontmatter import parse as parse_frontmatter

PROMPT_PATH = Path(__file__).resolve().parents[2] / "12_prompts" / "text.markdown.format.task.md"


class _MarkdownExecutor(Protocol):
    def invoke(self, payload: dict) -> dict: ...


def load_prompt() -> str:
    return parse_frontmatter(
        PROMPT_PATH.read_text(encoding="utf-8"), source_path=str(PROMPT_PATH)
    ).body


def format_markdown_with_lmstudio(
    file_path: str,
    model: str = "qwen/qwen3.6-27b",
    executor: _MarkdownExecutor | None = None,
) -> str:
    """Format a markdown file using LM Studio (or an injected executor).

    Args:
        file_path: Path to the markdown file to format.
        model: LM Studio model identifier.
        executor: Optional harness-like object with an ``invoke`` method. When
            omitted, an ``LMStudioHarness`` is constructed with default settings.
            Inject a fake executor in tests to avoid network calls.
    """
    content = Path(file_path).read_text(encoding="utf-8")
    prompt_template = load_prompt()
    prompt = prompt_template.replace("{{markdown_content}}", content)

    if executor is None:
        from harnesses.lmstudio import harness as lmstudio

        executor = lmstudio.LMStudioHarness(
            {
                "base_url": "http://localhost:1234/v1",
                "model": model,
                "api_key": "lm-studio",
            }
        )

    response = executor.invoke(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
        }
    )
    return response["choices"][0]["message"]["content"]
