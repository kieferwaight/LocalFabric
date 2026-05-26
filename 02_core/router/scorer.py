"""
scorer.py — Score candidate execution routes by confidence.

The scorer takes a TaskProfile and the list of currently available routes,
then returns a ranked list of RouteCandidate objects with confidence scores.

Scoring factors (v1 — rule-based with historical weight overlay):
  1. Intent → route affinity (hard-coded per-intent preferences)
  2. Complexity tier match (LOCAL / HYBRID / FRONTIER / AGENT)
  3. Route availability (is the service reachable right now?)
  4. Historical performance weight (loaded from feedback.json, falls back to 1.0)

Usage:
    from router.scorer import Scorer, RouteCandidate
    from router.classifier import Classifier

    clf = Classifier()
    scorer = Scorer()

    profile = clf.classify("run pytest and show me the failures")
    candidates = scorer.score(profile)
    best = candidates[0]
    print(best.route_id, best.score)
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Optional

from router.classifier import Intent, Complexity, TaskProfile

# ------------------------------------------------------------------
# Route registry
# ------------------------------------------------------------------

# Each route is identified by a string ID.
# Add new routes here as the system grows.

ROUTES = {
    # Local routes (free, fast)
    "local_research":    {"tier": Complexity.LOCAL,    "description": "local_research_scaffold via Ollama"},
    "local_tests":       {"tier": Complexity.LOCAL,    "description": "run_local_tests via subprocess"},
    "local_embed":       {"tier": Complexity.LOCAL,    "description": "sweep + embed via nomic-embed-text"},
    "local_query":       {"tier": Complexity.LOCAL,    "description": "query_local_knowledge via LanceDB"},
    # Hybrid routes
    "hybrid_research":   {"tier": Complexity.HYBRID,   "description": "local pre-process + frontier summarize"},
    # Frontier routes (paid)
    "frontier_claude":   {"tier": Complexity.FRONTIER, "description": "Claude API (claude-sonnet / claude-opus)"},
    "frontier_gemini":   {"tier": Complexity.FRONTIER, "description": "Google Gemini API"},
    "frontier_codex":    {"tier": Complexity.FRONTIER, "description": "OpenAI Codex / GPT-4o"},
    # Agent routes
    "agent_research":    {"tier": Complexity.AGENT,    "description": "multi-step research agent"},
    "agent_code":        {"tier": Complexity.AGENT,    "description": "multi-step code generation + test agent"},
}

# Intent → preferred route IDs (ordered by preference)
_INTENT_ROUTE_MAP: dict[Intent, list[str]] = {
    Intent.RESEARCH:  ["local_research", "hybrid_research", "frontier_claude"],
    Intent.TESTING:   ["local_tests"],
    Intent.CODE_FIX:  ["frontier_claude", "frontier_codex", "hybrid_research"],
    Intent.CODE_GEN:  ["frontier_claude", "frontier_codex", "frontier_gemini"],
    Intent.EMBED:     ["local_embed"],
    Intent.QUERY:     ["local_query"],
    Intent.SUMMARIZE: ["local_research", "hybrid_research", "frontier_claude"],
    Intent.ROUTE:     ["frontier_claude"],
    Intent.UNKNOWN:   ["local_research", "frontier_claude"],
}

_FEEDBACK_PATH = os.path.expanduser("~/.local_router_cache/feedback.json")


# ------------------------------------------------------------------
# RouteCandidate
# ------------------------------------------------------------------

@dataclass
class RouteCandidate:
    route_id: str
    score: float              # 0.0 – 1.0 (higher = better)
    tier: Complexity
    description: str
    available: bool = True
    score_breakdown: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "route_id": self.route_id,
            "score": round(self.score, 4),
            "tier": self.tier.value,
            "description": self.description,
            "available": self.available,
            "breakdown": self.score_breakdown,
        }


# ------------------------------------------------------------------
# Scorer
# ------------------------------------------------------------------

class Scorer:
    """
    Score and rank candidate routes for a given TaskProfile.

    Historical weights are loaded from ~/.local_router_cache/feedback.json
    (written by feedback.py). If the file doesn't exist, all weights default to 1.0.
    """

    def __init__(self, feedback_path: str = _FEEDBACK_PATH) -> None:
        self._feedback_path = feedback_path
        self._weights: dict[str, float] = self._load_weights()

    def _load_weights(self) -> dict[str, float]:
        if os.path.exists(self._feedback_path):
            try:
                with open(self._feedback_path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                return data.get("route_weights", {})
            except (json.JSONDecodeError, OSError):
                pass
        return {}

    def reload_weights(self) -> None:
        """Reload historical weights from disk (call after feedback.py updates)."""
        self._weights = self._load_weights()

    def score(
        self,
        profile: TaskProfile,
        available_routes: Optional[set[str]] = None,
    ) -> list[RouteCandidate]:
        """
        Return all routes ranked by score for *profile*.

        Args:
            profile:          TaskProfile from Classifier.classify().
            available_routes: Set of currently reachable route IDs.
                              If None, all routes are treated as available.

        Returns:
            List of RouteCandidate, sorted descending by score.
        """
        candidates: list[RouteCandidate] = []

        for route_id, meta in ROUTES.items():
            tier = meta["tier"]
            desc = meta["description"]
            is_available = (available_routes is None) or (route_id in available_routes)

            breakdown: dict[str, float] = {}

            # 1. Intent affinity — position in the preferred list for this intent
            preferred = _INTENT_ROUTE_MAP.get(profile.primary_intent(), [])
            if route_id in preferred:
                rank = preferred.index(route_id)
                affinity = max(0.0, 1.0 - rank * 0.25)   # 1st=1.0, 2nd=0.75, 3rd=0.50 …
            else:
                affinity = 0.1   # small non-zero so non-preferred routes are still ranked

            breakdown["intent_affinity"] = affinity

            # 2. Complexity tier match
            tier_match = self._tier_match(profile.complexity, tier)
            breakdown["tier_match"] = tier_match

            # 3. Classifier confidence boost
            confidence_boost = profile.confidence * 0.1
            breakdown["confidence_boost"] = round(confidence_boost, 3)

            # 4. Historical weight (default 1.0 if no data)
            hist_weight = self._weights.get(route_id, 1.0)
            breakdown["historical_weight"] = hist_weight

            # Composite score
            raw = (affinity * 0.5) + (tier_match * 0.3) + confidence_boost
            score = min(1.0, raw * hist_weight)
            breakdown["final"] = round(score, 4)

            # Penalise unavailable routes rather than exclude them
            if not is_available:
                score *= 0.05

            candidates.append(RouteCandidate(
                route_id=route_id,
                score=score,
                tier=tier,
                description=desc,
                available=is_available,
                score_breakdown=breakdown,
            ))

        candidates.sort(key=lambda c: c.score, reverse=True)
        return candidates

    @staticmethod
    def _tier_match(profile_complexity: Complexity, route_tier: Complexity) -> float:
        """Return a score for how well the route tier matches the task complexity."""
        order = [Complexity.LOCAL, Complexity.HYBRID, Complexity.FRONTIER, Complexity.AGENT]
        p_idx = order.index(profile_complexity)
        r_idx = order.index(route_tier)
        distance = abs(p_idx - r_idx)
        # Exact match = 1.0; one tier off = 0.6; two off = 0.3; three off = 0.1
        return [1.0, 0.6, 0.3, 0.1][min(distance, 3)]


if __name__ == "__main__":
    from router.classifier import Classifier

    clf = Classifier()
    scorer = Scorer()

    tasks = [
        "Run the test suite and show me what's failing",
        "Research how FastMCP handles async tools",
        "Write a new Python class for chunking YAML files",
    ]
    for task in tasks:
        profile = clf.classify(task)
        candidates = scorer.score(profile)
        print(f"\n> {task[:65]}")
        print(f"  Intent: {profile.primary_intent().value}  Complexity: {profile.complexity.value}")
        for c in candidates[:3]:
            avail = "✓" if c.available else "✗"
            print(f"  {avail} [{c.score:.3f}] {c.route_id} — {c.description}")
