"""
dispatcher.py — Execute the selected route and return a result.

The dispatcher is the execution layer of the routing pipeline. It receives
the top-ranked RouteCandidate (from scorer.py) and invokes it via the YAML
runtime:

    runtime.execute(route_id, arguments={"task": task, "context": context})

For FRONTIER / AGENT routes whose `deferred_model` is set, the dispatcher
returns a DEFERRED result rather than calling the model directly — the MCP
client or agent is responsible for making the actual API call.

Usage:
    from core.router.classifier import Classifier
    from core.router.scorer import Scorer
    from core.router.dispatcher import Dispatcher
    from core.runtimes.yaml.src import Runtime

    r = Runtime(workflow_dir='02_core/runtimes/yaml')
    r.import_yaml('02_core/runtimes/yaml/definitions/stdlib.yaml')
    r.execute('stdlib.load-modules', {})

    clf = Classifier()
    scorer = Scorer(runtime=r)
    dispatcher = Dispatcher(runtime=r)

    profile = clf.classify("run pytest")
    candidates = scorer.score(profile)
    result = dispatcher.dispatch(task="run pytest", candidates=candidates)
    print(result.output)
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from router.scorer import RouteCandidate, Complexity


# ------------------------------------------------------------------
# Dispatch result
# ------------------------------------------------------------------

class ResultStatus(str, Enum):
    SUCCESS  = "success"
    FAILURE  = "failure"
    DEFERRED = "deferred"   # frontier route — caller must invoke the model


@dataclass
class DispatchResult:
    route_id: str
    status: ResultStatus
    output: str
    elapsed_sec: float = 0.0
    deferred_model: Optional[str] = None   # set when status == DEFERRED
    deferred_prompt: Optional[str] = None  # set when status == DEFERRED
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "route_id": self.route_id,
            "status": self.status.value,
            "output": self.output,
            "elapsed_sec": round(self.elapsed_sec, 3),
            "deferred_model": self.deferred_model,
            "error": self.error,
        }


# ------------------------------------------------------------------
# Dispatcher
# ------------------------------------------------------------------

class Dispatcher:
    """
    Execute the best available route for a task via the YAML runtime.

    For routes with a `deferred_model` set and tier FRONTIER/AGENT: returns a
    DEFERRED result with model + prompt so the MCP client or agent can make
    the actual API call.

    For all other routes: calls runtime.execute(route_id, arguments={...})
    and returns the scope dict as the output.

    Args:
        runtime: Runtime instance with stdlib modules already loaded.
                 Required for actual route execution; if None, all dispatches
                 return FAILURE (useful as a null dispatcher in tests).
    """

    def __init__(self, runtime=None) -> None:
        self._runtime = runtime

    def dispatch(
        self,
        task: str,
        candidates: list[RouteCandidate],
        context: Optional[str] = None,
        max_fallbacks: int = 2,
    ) -> DispatchResult:
        """
        Execute the highest-scoring available route, with up to *max_fallbacks*
        fallbacks if execution fails.

        Args:
            task:           Raw task description / query string.
            candidates:     Ranked list from Scorer.score().
            context:        Optional pre-retrieved context (e.g. from query_knowledge).
            max_fallbacks:  How many additional routes to try on failure.

        Returns:
            DispatchResult
        """
        available = [c for c in candidates if c.available]
        if not available:
            return DispatchResult(
                route_id="none",
                status=ResultStatus.FAILURE,
                output="No available routes found.",
                error="all routes unavailable",
            )

        attempts = available[:max_fallbacks + 1]
        last_result: Optional[DispatchResult] = None

        for candidate in attempts:
            t0 = time.time()
            try:
                result = self._execute(task, candidate, context)
                result.elapsed_sec = time.time() - t0
                if result.status != ResultStatus.FAILURE:
                    return result
                last_result = result
            except Exception as exc:
                last_result = DispatchResult(
                    route_id=candidate.route_id,
                    status=ResultStatus.FAILURE,
                    output="",
                    elapsed_sec=time.time() - t0,
                    error=str(exc),
                )

        return last_result or DispatchResult(
            route_id="none",
            status=ResultStatus.FAILURE,
            output="All dispatch attempts failed.",
        )

    def _execute(
        self,
        task: str,
        candidate: RouteCandidate,
        context: Optional[str],
    ) -> DispatchResult:
        """Invoke the route via runtime.execute, or defer for frontier routes."""
        rid = candidate.route_id

        if self._runtime is None:
            return DispatchResult(
                route_id=rid,
                status=ResultStatus.FAILURE,
                output="",
                error="Dispatcher has no runtime; cannot execute route.",
            )

        # FRONTIER / AGENT routes with a deferred_model: hand off to the caller.
        if candidate.tier in (Complexity.FRONTIER, Complexity.AGENT):
            # Check if the catalog entry carries a deferred_model.
            deferred_model = self._get_deferred_model(rid)
            if deferred_model:
                return self._defer_to_frontier(task, candidate, context, deferred_model)

        # All other routes: call through the YAML runtime.
        try:
            ctx_arg: Any = {}
            if isinstance(context, dict):
                ctx_arg = context
            elif context is not None:
                ctx_arg = {"raw": context}

            scope = self._runtime.execute(
                rid,
                arguments={"task": task, "context": ctx_arg},
            )
            import json as _json
            output = _json.dumps(scope, default=str)
            return DispatchResult(
                route_id=rid,
                status=ResultStatus.SUCCESS,
                output=output,
            )
        except Exception as exc:
            return DispatchResult(
                route_id=rid,
                status=ResultStatus.FAILURE,
                output="",
                error=str(exc),
            )

    def _get_deferred_model(self, route_id: str) -> Optional[str]:
        """Look up the deferred_model variable for a route from the catalog."""
        if self._runtime is None:
            return None
        try:
            assembled = self._runtime.assemble_definition_frame(route_id)
            value = assembled.variables.get("deferred_model") or ""
            return str(value) if value else None
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Frontier / agent deferral
    # ------------------------------------------------------------------

    def _defer_to_frontier(
        self,
        task: str,
        candidate: RouteCandidate,
        context: Optional[str],
        deferred_model: str,
    ) -> DispatchResult:
        """
        Build a frontier prompt and return a DEFERRED result.
        The MCP client or agent is responsible for making the actual API call.
        """
        prompt = self._build_frontier_prompt(task, context)
        return DispatchResult(
            route_id=candidate.route_id,
            status=ResultStatus.DEFERRED,
            output=f"[Deferred to {deferred_model}]\n\n{prompt}",
            deferred_model=deferred_model,
            deferred_prompt=prompt,
        )

    @staticmethod
    def _build_frontier_prompt(task: str, context: Optional[str]) -> str:
        parts = []
        if context:
            parts.append(f"## Local Context\n\n{context}\n")
        parts.append(f"## Task\n\n{task}")
        return "\n".join(parts)
