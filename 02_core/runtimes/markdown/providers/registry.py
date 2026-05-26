"""Provider registry — frontmatter ``provider:`` names → constructor."""

from __future__ import annotations

from collections.abc import Callable, Mapping

from .base import MarkdownProvider
from .claude import ClaudeProvider

#: Public name → callable returning a configured provider. Callables (rather
#: than instances) let tests inject pre-built or stub providers without
#: mutating shared state.
PROVIDERS: dict[str, Callable[[], MarkdownProvider]] = {
    "claude": ClaudeProvider,
}


def register_provider(name: str, factory: Callable[[], MarkdownProvider]) -> None:
    """Register or override a provider by name. Used by tests and plugins."""
    PROVIDERS[name] = factory


def get_provider(
    name: str, *, overrides: Mapping[str, MarkdownProvider] | None = None
) -> MarkdownProvider:
    """Resolve a provider by frontmatter name.

    ``overrides`` lets a caller (most often a test or the CLI adapter)
    substitute a specific provider instance for one or more names without
    touching the global ``PROVIDERS`` registry.
    """
    if overrides and name in overrides:
        return overrides[name]
    if name not in PROVIDERS:
        known = ", ".join(sorted(PROVIDERS)) or "<none>"
        raise KeyError(f"Unknown markdown provider {name!r}; known providers: {known}")
    return PROVIDERS[name]()
