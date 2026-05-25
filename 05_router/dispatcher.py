"""
dispatcher.py — Execute the selected route and return a result.

The dispatcher is the execution layer of the routing pipeline. It receives
the top-ranked RouteCandidate (from scorer.py) and calls the appropriate
local tool, hybrid pipeline, or frontier model adapter.

v1 implements local routes directly. Frontier routes return a structured
stub that tells the calling agent which model to use and with what prompt —
actual frontier API calls are the responsibility of the agent/MCP client.

Usage:
    from router.classifier import Classifier
    from router.scorer import Scorer
    from router.dispatcher import Dispatcher

    clf = Classifier()
    scorer = Scorer()
    dispatcher = Dispatcher()

    profile = clf.classify("run pytest")
    candidates = scorer.score(profile)
    result = dispatcher.dispatch(task="run pytest", candidates=candidates)
    print(result.output)
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from router.scorer import RouteCandidate, Complexity

# Bucket directories (02_core, 04_harnesses, 05_router, 07_tools, 08_drivers,
# 11_mcp, etc.) must be on PYTHONPATH for cross-bucket imports to resolve.
# This will be handled by the workspace-level pyproject.toml we add later.


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
    Execute the best available route for a task.

    For local routes: calls the tool directly and returns the output.
    For frontier routes: returns a DEFERRED result with model + prompt,
    so the MCP client or agent can make the actual API call.
    """

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
        """Route to the correct handler based on route_id."""
        rid = candidate.route_id

        if rid == "local_research":
            return self._local_research(task, candidate)
        elif rid == "local_tests":
            return self._local_tests(task, candidate)
        elif rid == "local_embed":
            return self._local_embed(task, candidate)
        elif rid == "local_query":
            return self._local_query(task, candidate)
        elif rid == "hybrid_research":
            return self._hybrid_research(task, candidate, context)
        elif candidate.tier in (Complexity.FRONTIER, Complexity.AGENT):
            return self._defer_to_frontier(task, candidate, context)
        else:
            return DispatchResult(
                route_id=rid,
                status=ResultStatus.FAILURE,
                output="",
                error=f"No handler implemented for route: {rid}",
            )

    # ------------------------------------------------------------------
    # Local handlers
    # ------------------------------------------------------------------

    def _local_research(self, task: str, c: RouteCandidate) -> DispatchResult:
        from workflows.research.local import local_research_scaffold
        output = local_research_scaffold(task)
        return DispatchResult(route_id=c.route_id, status=ResultStatus.SUCCESS, output=output)

    def _local_tests(self, task: str, c: RouteCandidate) -> DispatchResult:
        from tools.shell.run_tests import run_local_tests
        # Extract command from task if present (e.g. "run pytest -k smoke")
        command = "pytest"
        lower = task.lower()
        for kw in ("pytest", "npm test", "python -m pytest", "make test"):
            if kw in lower:
                # Grab from the keyword to end of line
                idx = lower.index(kw)
                command = task[idx:].split("\n")[0].strip()
                break
        output = run_local_tests(command)
        status = ResultStatus.SUCCESS if "SUCCESS" in output else ResultStatus.FAILURE
        return DispatchResult(route_id=c.route_id, status=status, output=output)

    def _local_embed(self, task: str, c: RouteCandidate) -> DispatchResult:
        try:
            from tools.embeddings.sweep import sweep
            stats = sweep(dry_run=False)
            output = (
                f"Sweep complete — {stats['files_changed']} files changed, "
                f"{stats['chunks_added']} chunks added in {stats['elapsed_sec']}s."
            )
            return DispatchResult(route_id=c.route_id, status=ResultStatus.SUCCESS, output=output)
        except Exception as exc:
            return DispatchResult(
                route_id=c.route_id, status=ResultStatus.FAILURE, output="", error=str(exc)
            )

    def _local_query(self, task: str, c: RouteCandidate) -> DispatchResult:
        try:
            from tools.embeddings.query import LocalKnowledgeQuery
            lkq = LocalKnowledgeQuery()
            output = lkq.query(task)
            return DispatchResult(route_id=c.route_id, status=ResultStatus.SUCCESS, output=output)
        except Exception as exc:
            return DispatchResult(
                route_id=c.route_id, status=ResultStatus.FAILURE, output="", error=str(exc)
            )

    def _hybrid_research(
        self, task: str, c: RouteCandidate, context: Optional[str]
    ) -> DispatchResult:
        """Local pre-process → return deferred prompt for frontier completion."""
        from workflows.research.local import local_research_scaffold
        local_summary = local_research_scaffold(task)
        deferred_prompt = self._build_hybrid_prompt(task, local_summary, context)
        return DispatchResult(
            route_id=c.route_id,
            status=ResultStatus.DEFERRED,
            output=local_summary,
            deferred_model="claude-sonnet",
            deferred_prompt=deferred_prompt,
        )

    # ------------------------------------------------------------------
    # Frontier / agent deferral
    # ------------------------------------------------------------------

    def _defer_to_frontier(
        self, task: str, c: RouteCandidate, context: Optional[str]
    ) -> DispatchResult:
        """
        Build a frontier prompt and return a DEFERRED result.
        The MCP client or agent is responsible for making the actual API call.
        """
        model = self._select_model(c)
        prompt = self._build_frontier_prompt(task, context)
        return DispatchResult(
            route_id=c.route_id,
            status=ResultStatus.DEFERRED,
            output=f"[Deferred to {model}]\n\n{prompt}",
            deferred_model=model,
            deferred_prompt=prompt,
        )

    @staticmethod
    def _select_model(c: RouteCandidate) -> str:
        if "claude" in c.route_id:
            return "claude-sonnet-4-6"
        elif "gemini" in c.route_id:
            return "gemini-2.0-flash"
        elif "codex" in c.route_id:
            return "gpt-4o"
        return "claude-sonnet-4-6"  # default

    @staticmethod
    def _build_frontier_prompt(task: str, context: Optional[str]) -> str:
        parts = []
        if context:
            parts.append(f"## Local Context\n\n{context}\n")
        parts.append(f"## Task\n\n{task}")
        return "\n".join(parts)

    @staticmethod
    def _build_hybrid_prompt(task: str, local_summary: str, context: Optional[str]) -> str:
        parts = []
        if context:
            parts.append(f"## Local Knowledge Base Context\n\n{context}\n")
        parts.append(f"## Local Pre-processed Summary\n\n{local_summary}\n")
        parts.append(f"## Original Task\n\n{task}")
        return "\n".join(parts)


if __name__ == "__main__":
    from router.classifier import Classifier
    from router.scorer import Scorer

    clf = Classifier()
    scorer = Scorer()
    dispatcher = Dispatcher()

    task = "Run pytest and tell me what's failing"
    profile = clf.classify(task)
    candidates = scorer.score(profile)
    result = dispatcher.dispatch(task=task, candidates=candidates)

    print(f"Route: {result.route_id}")
    print(f"Status: {result.status.value}")
    print(f"Output:\n{result.output[:500]}")
