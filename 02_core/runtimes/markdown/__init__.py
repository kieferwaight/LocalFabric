"""Markdown runtime harness — compiles `.md` files into the YAML runtime."""

from __future__ import annotations

from .compiler import PROVIDER_MARKER_KEY, MarkdownCompileError, compile_text
from .harness import MarkdownHarness
from .providers import (
    PROVIDERS,
    ClaudeProvider,
    MarkdownProvider,
    ProviderError,
    ProviderResult,
)

__all__ = [
    "MarkdownHarness",
    "MarkdownCompileError",
    "PROVIDER_MARKER_KEY",
    "compile_text",
    "MarkdownProvider",
    "ProviderError",
    "ProviderResult",
    "ClaudeProvider",
    "PROVIDERS",
]
