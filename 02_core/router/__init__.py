"""
router — Decision engine for the Local LLM Router MCP.

Modules:
    classifier    — classify incoming task intent and complexity
    scorer        — score candidate execution routes by confidence
    dispatcher    — execute the selected route (local / frontier / tool / agent)
    feedback      — log outcomes and update route weights over time
    policy        — cost/latency/capability constraints used by the scorer
    router        — thin orchestrator wiring Classifier → Scorer → Dispatcher
    catalog_loader — load route definitions from the YAML runtime catalog
"""

from router.catalog_loader import RouteEntry, load_routes
from router.classifier import Classifier, Complexity, Intent, TaskProfile
from router.dispatcher import Dispatcher, DispatchResult, ResultStatus
from router.feedback import FeedbackEntry, FeedbackLogger
from router.policy import Policy
from router.router import Router
from router.scorer import RouteCandidate, Scorer

__all__ = [
    "RouteEntry",
    "load_routes",
    "Classifier",
    "Complexity",
    "Intent",
    "TaskProfile",
    "Dispatcher",
    "DispatchResult",
    "ResultStatus",
    "FeedbackEntry",
    "FeedbackLogger",
    "Policy",
    "Router",
    "RouteCandidate",
    "Scorer",
]
