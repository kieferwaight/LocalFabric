"""Harness-backed vision task execution for the image intelligence workflow."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from core.runtimes.markdown.frontmatter import parse as parse_frontmatter
from harnesses.ollama import OllamaHarness

_PROMPTS_DIR = Path(__file__).resolve().parents[3] / "12_prompts"
_TASKS = ("overview", "layout", "style")
_DEFAULT_VISION_MODEL = "llama3.2-vision"
_OPTIONS = {
    "temperature": 0.0,
    "top_p": 0.8,
    "top_k": 20,
    "repeat_penalty": 1.35,
    "repeat_last_n": 256,
    "num_predict": 180,
    "stop": ["<END>", "\n## END", "\n--- END"],
}


def _read_prompt(task: str) -> str:
    if task not in {*_TASKS, "visible-text"}:
        raise ValueError(f"Unknown vision task: {task}")
    path = _PROMPTS_DIR / f"image.vision.{task}.task.md"
    return parse_frontmatter(path.read_text(encoding="utf-8"), source_path=str(path)).body.strip()


def _encode_image(path: Path) -> str:
    with path.open("rb") as handle:
        return base64.standard_b64encode(handle.read()).decode("utf-8")


def run_vision_task(
    path: Path,
    task: str,
    model: str | None = None,
    harness: OllamaHarness | None = None,
) -> str:
    """Execute one named vision task through the Ollama harness."""
    chosen_model = model or _DEFAULT_VISION_MODEL
    executor = harness or OllamaHarness(
        {
            "model": chosen_model,
            "manage_server": False,
        }
    )
    response: dict[str, Any] = executor.invoke(
        {
            "model": chosen_model,
            "messages": [
                {
                    "role": "user",
                    "content": _read_prompt(task),
                    "images": [_encode_image(path)],
                }
            ],
            "options": _OPTIONS,
        }
    )
    return str(response.get("message", {}).get("content", response.get("response", ""))).strip()


def describe_image(path: Path, model: str | None = None) -> dict[str, str]:
    """Run the standard visual-description task set sequentially."""
    return {task: run_vision_task(path, task, model=model) for task in _TASKS}
