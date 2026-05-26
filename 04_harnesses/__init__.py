"""Harness layer — execution lifecycle controllers for providers and services.

Owns invoke/stream/retry/logs/health for a single provider, model, or service.
Adapters translate inbound requests; harnesses run them.

Available harnesses:
    ClaudeHarness          — Anthropic Claude (claude/)
    CodexHarness           — OpenAI Codex CLI (codex/)
    GeminiHarness          — Google Gemini (gemini/)
    LMStudioHarness        — LM Studio local server (lmstudio/)
    MarkdownHarness        — markdown prompt runtime (markdown/)
    OllamaHarness          — Ollama local server (ollama/)
    OpenAIHarness          — OpenAI API (openai/)

Docker service lifecycle is no longer a Python harness — the
docker.base / compose.up / compose.down YAML definitions own that role
(see 02_core/runtimes/yaml/definitions/docker.yaml).
"""

from harnesses.base import Harness, HarnessError, HarnessStatus
from harnesses.claude import ClaudeHarness
from harnesses.codex import CodexHarness
from harnesses.gemini import GeminiHarness
from harnesses.lmstudio import LMStudioHarness
from harnesses.markdown import MarkdownHarness
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
    "MarkdownHarness",
    "OllamaHarness",
    "OpenAIHarness",
]
