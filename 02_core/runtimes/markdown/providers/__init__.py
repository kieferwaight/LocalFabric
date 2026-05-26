"""Provider plugins for the markdown harness.

When a markdown file declares ``provider:`` in its frontmatter, the markdown
harness routes execution to one of these providers instead of compiling the
body into a fence-block YAML definition. Providers expose a single
``run(prompt, ...)`` method and remain decoupled from the YAML runtime.
"""

from __future__ import annotations

from .base import MarkdownProvider, ProviderError, ProviderResult
from .claude import ClaudeProvider
from .registry import PROVIDERS, get_provider, register_provider

__all__ = [
    "MarkdownProvider",
    "ProviderError",
    "ProviderResult",
    "ClaudeProvider",
    "PROVIDERS",
    "get_provider",
    "register_provider",
]
