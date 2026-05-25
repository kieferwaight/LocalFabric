"""
router.py — Thin orchestrator wiring Classifier → Scorer → Dispatcher.

The Router is the single entry point most callers want: hand it a task string
(plus optional context) and it produces a DispatchResult. It composes the
three stages of the pipeline so callers don't have to chain them by hand.

Usage:
    from router import Router

    r = Router()
    result = r.route("Run pytest and tell me what's failing")
    print(result.status, result.output)
"""

from __future__ import annotations

from typing import Optional

from router.classifier import Classifier, TaskProfile
from router.dispatcher import Dispatcher, DispatchResult
from router.policy import Policy
from router.scorer import RouteCandidate, Scorer


class Router:
    """
    Compose Classifier → Scorer → Dispatcher into a single ``route()`` call.

    Each stage is held as an attribute so callers can replace it (e.g. inject
    a mock Dispatcher in tests) without subclassing.
    """

    def __init__(
        self,
        classifier: Optional[Classifier] = None,
        scorer: Optional[Scorer] = None,
        dispatcher: Optional[Dispatcher] = None,
        policy: Optional[Policy] = None,
    ) -> None:
        self.classifier = classifier or Classifier()
        self.scorer = scorer or Scorer()
        self.dispatcher = dispatcher or Dispatcher()
        self.policy = policy or Policy()

    def route(
        self,
        task: str,
        context: Optional[str] = None,
        available_routes: Optional[set[str]] = None,
    ) -> DispatchResult:
        """
        Classify *task*, score candidate routes, and dispatch the best one.

        Args:
            task:             Raw task description / query string.
            context:          Optional pre-retrieved context (e.g. local KB hit).
            available_routes: Set of currently reachable route IDs.
                              If None, all routes are treated as available.

        Returns:
            DispatchResult from Dispatcher.dispatch().
        """
        profile = self.classify(task)
        candidates = self.score(profile, available_routes=available_routes)
        return self.dispatcher.dispatch(
            task=task,
            candidates=candidates,
            context=context,
            max_fallbacks=self.policy.max_fallbacks,
        )

    def classify(self, task: str) -> TaskProfile:
        """Stage 1: produce a TaskProfile from a raw task string."""
        return self.classifier.classify(task)

    def score(
        self,
        profile: TaskProfile,
        available_routes: Optional[set[str]] = None,
    ) -> list[RouteCandidate]:
        """
        Stage 2: rank routes for a TaskProfile, filtered by policy.

        Routes whose tier is disallowed by the current Policy are dropped
        entirely (rather than penalised) so the dispatcher never sees them.
        """
        candidates = self.scorer.score(profile, available_routes=available_routes)
        return [c for c in candidates if self.policy.allows_tier(c.tier)]


if __name__ == "__main__":
    r = Router()
    task = "Run pytest and tell me what's failing"
    result = r.route(task)

    print(f"Route: {result.route_id}")
    print(f"Status: {result.status.value}")
    print(f"Output:\n{result.output[:500]}")
