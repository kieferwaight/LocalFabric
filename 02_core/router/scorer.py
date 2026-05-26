"""
scorer.py — Score candidate execution routes by confidence.

The scorer takes a TaskProfile and the list of currently available routes,
then returns a ranked list of RouteCandidate objects with confidence scores.

Routes are now loaded from the YAML runtime catalog (every definition
descended from `route.base` and tagged `has_route=True`) rather than
a hardcoded dict. The catalog loader is invoked at construction time;
call `reload_routes()` to refresh after catalog changes.

Scoring factors (v1 — rule-based with historical weight overlay):
  1. Intent → route affinity (declared per-route as `intent_affinity` variable)
  2. Complexity tier match (LOCAL / HYBRID / FRONTIER / AGENT)
  3. Route availability (is the service reachable right now?)
  4. Historical performance weight (loaded from feedback.json, falls back to 1.0)

Usage:
    from core.router.scorer import Scorer, RouteCandidate
    from core.router.classifier import Classifier
    from core.runtimes.yaml.src import Runtime

    r = Runtime(workflow_dir='02_core/runtimes/yaml')
    r.import_yaml('02_core/runtimes/yaml/definitions/stdlib.yaml')
    r.execute('stdlib.load-modules', {})

    clf = Classifier()
    scorer = Scorer(runtime=r)

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
from router.catalog_loader import RouteEntry, load_routes

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
# Helpers
# ------------------------------------------------------------------

def _tier_from_str(tier_str: str) -> Complexity:
    """Map a tier string from a RouteEntry to the Complexity enum."""
    mapping = {
        "LOCAL":    Complexity.LOCAL,
        "HYBRID":   Complexity.HYBRID,
        "FRONTIER": Complexity.FRONTIER,
        "AGENT":    Complexity.AGENT,
        # lower-case aliases (in case someone writes them that way in YAML)
        "local":    Complexity.LOCAL,
        "hybrid":   Complexity.HYBRID,
        "frontier": Complexity.FRONTIER,
        "agent":    Complexity.AGENT,
    }
    return mapping.get(tier_str, Complexity.LOCAL)


def _affinity_score(intent: Intent, entry: RouteEntry) -> float:
    """
    Return an affinity score for a single route entry given the primary intent.

    The `intent_affinity` field on a route is a list of intent label strings
    (e.g. ["RESEARCH", "SUMMARIZE"]). The position in the list gives a falloff:
      1st = 1.0, 2nd = 0.75, 3rd = 0.50, … clamped to 0.0 minimum.
    Routes that don't list the intent get a small non-zero floor (0.1) so
    non-preferred routes are still ranked (not hidden entirely).
    """
    intent_label = intent.value.upper()
    affinity_list = [label.upper() for label in entry.intent_affinity]
    if intent_label in affinity_list:
        rank = affinity_list.index(intent_label)
        return max(0.0, 1.0 - rank * 0.25)
    return 0.1  # non-preferred floor


# ------------------------------------------------------------------
# Scorer
# ------------------------------------------------------------------

class Scorer:
    """
    Score and rank candidate routes for a given TaskProfile.

    Routes are loaded from the YAML runtime catalog at construction time.
    Historical weights are loaded from ~/.local_router_cache/feedback.json
    (written by feedback.py). If the file doesn't exist, all weights default
    to 1.0.

    Args:
        runtime:       Runtime instance with stdlib modules already loaded.
                       If None, the scorer returns an empty candidates list
                       (useful as a null scorer in tests that don't need routes).
        feedback_path: Override path for the feedback JSON file.
    """

    def __init__(
        self,
        runtime=None,
        feedback_path: str = _FEEDBACK_PATH,
    ) -> None:
        self._runtime = runtime
        self._feedback_path = feedback_path
        self._weights: dict[str, float] = self._load_weights()
        self._routes: list[RouteEntry] = self._load_routes()

    def _load_routes(self) -> list[RouteEntry]:
        if self._runtime is None:
            return []
        return load_routes(self._runtime)

    def reload_routes(self) -> None:
        """Reload routes from the catalog (call after catalog changes)."""
        self._routes = self._load_routes()

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

        for entry in self._routes:
            tier = _tier_from_str(entry.tier)
            is_available = (available_routes is None) or (entry.id in available_routes)

            breakdown: dict[str, float] = {}

            # 1. Intent affinity — position in the per-route intent_affinity list
            affinity = _affinity_score(profile.primary_intent(), entry)
            breakdown["intent_affinity"] = affinity

            # 2. Complexity tier match
            tier_match = self._tier_match(profile.complexity, tier)
            breakdown["tier_match"] = tier_match

            # 3. Classifier confidence boost
            confidence_boost = profile.confidence * 0.1
            breakdown["confidence_boost"] = round(confidence_boost, 3)

            # 4. Historical weight (default 1.0 if no data)
            hist_weight = self._weights.get(entry.id, 1.0)
            breakdown["historical_weight"] = hist_weight

            # Composite score
            raw = (affinity * 0.5) + (tier_match * 0.3) + confidence_boost
            score = min(1.0, raw * hist_weight)
            breakdown["final"] = round(score, 4)

            # Penalise unavailable routes rather than exclude them
            if not is_available:
                score *= 0.05

            candidates.append(RouteCandidate(
                route_id=entry.id,
                score=score,
                tier=tier,
                description=entry.description.strip(),
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
