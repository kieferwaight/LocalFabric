"""
feedback.py — Log route outcomes and update historical route weights.

Each dispatch result is recorded with its route, status, latency, and task metadata.
Route weights are computed as an exponential moving average (EMA) of success rates,
then persisted to ~/.local_router_cache/feedback.json for the scorer to load.

Usage:
    from router.feedback import FeedbackLogger
    from router.dispatcher import DispatchResult, ResultStatus

    logger = FeedbackLogger()
    logger.record(profile=profile, result=result)

    # Review stats
    print(logger.route_stats())
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass

from router.classifier import TaskProfile
from router.dispatcher import DispatchResult, ResultStatus

_FEEDBACK_PATH = os.path.expanduser("~/.local_router_cache/feedback.json")
_EMA_ALPHA = 0.2  # smoothing factor: 0 = ignore new data, 1 = use only new data


@dataclass
class FeedbackEntry:
    timestamp: float
    route_id: str
    status: str  # success / failure / deferred
    elapsed_sec: float
    intent: str
    complexity: str
    estimated_tokens: int
    error: str | None = None


class FeedbackLogger:
    """
    Persist route execution outcomes and maintain per-route success-rate weights.

    The weight for each route is an EMA of its binary success signal:
        weight(t) = alpha * success(t) + (1 - alpha) * weight(t-1)
    where success(t) = 1.0 for SUCCESS, 0.5 for DEFERRED, 0.0 for FAILURE.

    Weights are clamped to [0.1, 2.0] so a bad streak never fully silences a route.
    """

    def __init__(self, feedback_path: str = _FEEDBACK_PATH) -> None:
        self._path = feedback_path
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        self._data = self._load()

    # ------------------------------------------------------------------
    # Load / save
    # ------------------------------------------------------------------

    def _load(self) -> dict:
        if os.path.exists(self._path):
            try:
                with open(self._path, encoding="utf-8") as fh:
                    return json.load(fh)
            except (json.JSONDecodeError, OSError):
                pass
        return {"route_weights": {}, "log": []}

    def _save(self) -> None:
        # Keep only the last 1 000 log entries to avoid unbounded growth
        self._data["log"] = self._data["log"][-1000:]
        try:
            with open(self._path, "w", encoding="utf-8") as fh:
                json.dump(self._data, fh, indent=2)
        except OSError as exc:
            print(f"[Feedback] Warning: could not save feedback: {exc}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record(
        self,
        profile: TaskProfile,
        result: DispatchResult,
    ) -> None:
        """
        Record a dispatch outcome and update the route's EMA weight.

        Args:
            profile: TaskProfile from Classifier (for intent / complexity metadata).
            result:  DispatchResult from Dispatcher.
        """
        entry = FeedbackEntry(
            timestamp=time.time(),
            route_id=result.route_id,
            status=result.status.value,
            elapsed_sec=result.elapsed_sec,
            intent=profile.primary_intent().value,
            complexity=profile.complexity.value,
            estimated_tokens=profile.estimated_tokens,
            error=result.error,
        )

        # Append to log
        self._data["log"].append(entry.__dict__)

        # Update EMA weight
        success_signal = {
            ResultStatus.SUCCESS.value: 1.0,
            ResultStatus.DEFERRED.value: 0.5,
            ResultStatus.FAILURE.value: 0.0,
        }.get(result.status.value, 0.0)

        weights = self._data.setdefault("route_weights", {})
        current = weights.get(result.route_id, 1.0)
        updated = _EMA_ALPHA * success_signal + (1 - _EMA_ALPHA) * current
        weights[result.route_id] = round(max(0.1, min(2.0, updated)), 4)

        self._save()

    def route_stats(self) -> dict:
        """Return a summary of recorded outcomes per route."""
        from collections import defaultdict

        stats: dict[str, dict] = defaultdict(
            lambda: {"total": 0, "success": 0, "failure": 0, "deferred": 0}
        )
        for entry in self._data.get("log", []):
            rid = entry.get("route_id", "unknown")
            stats[rid]["total"] += 1
            status = entry.get("status", "unknown")
            if status in stats[rid]:
                stats[rid][status] += 1

        weights = self._data.get("route_weights", {})
        return {rid: {**data, "ema_weight": weights.get(rid, 1.0)} for rid, data in stats.items()}

    def clear(self) -> None:
        """Reset all feedback data (useful for testing)."""
        self._data = {"route_weights": {}, "log": []}
        self._save()


if __name__ == "__main__":
    import json as _json

    logger = FeedbackLogger()
    print("Current route stats:")
    print(_json.dumps(logger.route_stats(), indent=2))
