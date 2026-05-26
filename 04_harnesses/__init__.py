"""Harness layer — execution lifecycle controllers for providers and services.

Owns invoke/stream/retry/logs/health for a single provider, model, or service.
Adapters translate inbound requests; harnesses run them.

Available harnesses:
    ClaudeHarness          — Anthropic Claude (claude/)
    CodexHarness           — OpenAI Codex CLI (codex/)
    DockerServiceHarness   — Docker Compose service lifecycle (docker_service/)
    GeminiHarness          — Google Gemini (gemini/)
    LMStudioHarness        — LM Studio local server (lmstudio/)
    MarkdownHarness        — markdown prompt runtime (markdown/)
    OllamaHarness          — Ollama local server (ollama/)
    OpenAIHarness          — OpenAI API (openai/)
"""

from harnesses.base import Harness, HarnessError, HarnessStatus
from harnesses.claude import ClaudeHarness
from harnesses.codex import CodexHarness
from harnesses.docker_service import DockerServiceHarness
from harnesses.gemini import GeminiHarness
from harnesses.lmstudio import LMStudioHarness
from harnesses.markdown import MarkdownHarness
from harnesses.ollama import OllamaHarness
from harnesses.openai import OpenAIHarness

__all__ = [
    "ClaudeHarness",
    "CodexHarness",
    "DockerServiceHarness",
    "GeminiHarness",
    "Harness",
    "HarnessError",
    "HarnessStatus",
    "LMStudioHarness",
    "MarkdownHarness",
    "OllamaHarness",
    "OpenAIHarness",
]
