"""Provider plugins for the markdown harness.

When a markdown file declares ``provider:`` in its frontmatter, the markdown
harness routes execution to one of these providers instead of compiling the
body into a fence-block YAML definition. Providers expose a single
``run(prompt, ...)`` method and remain decoupled from the YAML runtime.
"""

from __future__ import annotations

from .base import MarkdownProvider, ProviderError, ProviderResult
from .claude import ClaudeProvider
from .claude_cli import ClaudeCliProvider
from .codex_cli import CodexCliProvider
from .copilot_cli import CopilotCliProvider
from .gemini_cli import GeminiCliProvider
from .lmstudio import LMStudioProvider
from .ollama import OllamaProvider
from .registry import PROVIDERS, get_provider, register_provider

__all__ = [
    "MarkdownProvider",
    "ProviderError",
    "ProviderResult",
    "ClaudeProvider",
    "OllamaProvider",
    "LMStudioProvider",
    "ClaudeCliProvider",
    "GeminiCliProvider",
    "CodexCliProvider",
    "CopilotCliProvider",
    "PROVIDERS",
    "get_provider",
    "register_provider",
]
