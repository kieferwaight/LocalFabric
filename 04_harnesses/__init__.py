"""Harness layer — execution lifecycle controllers for model providers.

Owns invoke/stream/retry/logs/health for a single provider. Adapters
translate inbound requests; harnesses run them.

Available harnesses:
    ClaudeHarness          — Anthropic Claude (claude/)
    CodexHarness           — OpenAI Codex CLI (codex/)
    GeminiHarness          — Google Gemini (gemini/)
    LMStudioHarness        — LM Studio local server (lmstudio/)
    OllamaHarness          — Ollama local server (ollama/)
    OpenAIHarness          — OpenAI API (openai/)

Two former occupants moved out:

- The markdown prompt runtime is no longer a harness — it lives at
  :mod:`core.runtimes.markdown` alongside the YAML runtime and the
  LangGraph runtime, since all three normalise to YAML.
- Docker service lifecycle is no longer a Python harness — the
  docker.base / compose.up.task / compose.down.task YAML definitions own that
  role (see 02_core/runtimes/yaml/definitions/docker.yaml).
"""

from harnesses.base import Harness, HarnessError, HarnessStatus
from harnesses.claude import ClaudeHarness
from harnesses.codex import CodexHarness
from harnesses.gemini import GeminiHarness
from harnesses.lmstudio import LMStudioHarness
from harnesses.ollama import OllamaHarness
from harnesses.openai import OpenAIHarness

__all__ = [
    "ClaudeHarness",
    "CodexHarness",
    "GeminiHarness",
    "Harness",
    "HarnessError",
    "HarnessStatus",
    "LMStudioHarness",
    "OllamaHarness",
    "OpenAIHarness",
]
