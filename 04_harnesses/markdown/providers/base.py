"""Provider contract for markdown-harness provider-style execution.

The markdown harness compiles ``provider:`` frontmatter files into a
``ProviderRequest`` and dispatches it through one of these implementations.
Providers wrap an existing harness (``harnesses.claude.ClaudeHarness``,
etc.); they do not call provider SDKs directly. That keeps API-client
concerns in the provider harness layer where they already live.
"""

from __future__ import annotations

import abc
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any


class ProviderError(RuntimeError):
    """Raised by markdown providers for any user-visible failure.

    Wraps the underlying ``HarnessError`` (or SDK exception) with a message
    that names the provider, so error output in the CLI is self-explanatory.
    """


@dataclass(frozen=True)
class ProviderResult:
    """Result of a provider-style markdown execution.

    ``text`` is the assistant's final response. ``model`` and ``usage`` echo
    whatever the upstream harness reports so callers (and tests) can assert
    on them. Streaming providers still produce a terminal ``ProviderResult``
    after the stream completes; the streamed chunks go straight to stdout.
    """

    text: str
    model: str = ""
    usage: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)


class MarkdownProvider(abc.ABC):
    """Minimal contract for a markdown-harness provider.

    Concrete providers receive a pre-rendered prompt string (with Jinja
    variables already substituted) and return a ``ProviderResult`` — or
    yield chunks of text when ``stream=True``.
    """

    #: Provider identifier matched against frontmatter ``provider:`` field.
    name: str = "provider"

    #: Fallback model id when the markdown file omits ``model:``. Subclasses
    #: override this; the markdown compiler does NOT bake the default in,
    #: so users can swap providers and pick up a sensible default per
    #: provider.
    default_model: str = ""

    @abc.abstractmethod
    def run(
        self,
        prompt: str,
        *,
        model: str | None = None,
        system: str | None = None,
        stream: bool = False,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> ProviderResult | Iterator[str]:
        """Execute one prompt against the upstream provider.

        ``model``/``system``/``max_tokens``/``temperature`` mirror the
        frontmatter fields the markdown harness accepts. When ``stream`` is
        true, return an iterator of text chunks; otherwise return a single
        ``ProviderResult``.
        """
