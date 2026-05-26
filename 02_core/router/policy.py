"""
policy.py — Cost, latency, and capability constraints used by the Scorer.

The Policy object centralises the soft constraints the router applies when
choosing among candidate routes. The Scorer (today) reads these implicitly
through default behaviour; this module makes the dependency explicit so
callers can swap in different policies (e.g. "local_only", "cheap", "fast").

Usage:
    from router.policy import Policy

    policy = Policy()                 # sensible defaults
    cheap  = Policy(max_cost_usd=0.0) # disable paid frontier routes
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from router.classifier import Complexity


@dataclass
class Policy:
    """Cost / latency / capability constraints applied at scoring time."""

    # Cost ceiling per task in USD. None = no ceiling.
    max_cost_usd: Optional[float] = None

    # Latency budget in seconds. None = no budget.
    max_latency_sec: Optional[float] = None

    # Allowed execution tiers (defaults to all four).
    allowed_tiers: set[Complexity] = field(
        default_factory=lambda: {
            Complexity.LOCAL,
            Complexity.HYBRID,
            Complexity.FRONTIER,
            Complexity.AGENT,
        }
    )

    # Required capabilities (e.g. "code_exec", "web_fetch"). Empty = none required.
    required_capabilities: set[str] = field(default_factory=set)

    # Prefer local routes whenever feasible (local-first design principle).
    prefer_local: bool = True

    # Hard ceiling on the number of fallback attempts the dispatcher will make.
    max_fallbacks: int = 2

    def allows_tier(self, tier: Complexity) -> bool:
        """Return True if *tier* is permitted under this policy."""
        return tier in self.allowed_tiers
