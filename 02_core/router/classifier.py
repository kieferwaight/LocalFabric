"""
classifier.py — Classify incoming task intent and complexity.

The classifier is the first stage of the routing pipeline. It takes a raw task
description and returns a TaskProfile — a structured summary of what kind of work
is being requested and how demanding it is.

Classification is intentionally rule-based for v1 (zero latency, zero cost, no model
required). The scorer then uses the TaskProfile to rank candidate routes.

Usage:
    from router.classifier import Classifier, TaskProfile

    clf = Classifier()
    profile = clf.classify("summarize the test runner output and fix the failing test")
    print(profile.intent)      # ["testing", "code_fix"]
    print(profile.complexity)  # "frontier"
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

# ------------------------------------------------------------------
# Enums
# ------------------------------------------------------------------


class Intent(str, Enum):
    """Primary task categories."""

    RESEARCH = "research"  # web fetch, summarize, investigate
    TESTING = "testing"  # run tests, check failures
    CODE_FIX = "code_fix"  # debug, patch, refactor
    CODE_GEN = "code_gen"  # write new code / scripts
    EMBED = "embed"  # chunk, index, embed files
    QUERY = "query"  # semantic search over knowledge base
    SUMMARIZE = "summarize"  # condense existing text
    ROUTE = "route"  # meta: route to another tool/agent
    UNKNOWN = "unknown"  # fallback


class Complexity(str, Enum):
    """Execution tier recommendation."""

    LOCAL = "local"  # local Ollama model (fastest, free)
    HYBRID = "hybrid"  # local pre-process → frontier for final answer
    FRONTIER = "frontier"  # requires a frontier model (Claude / Gemini / GPT)
    AGENT = "agent"  # multi-step autonomous agent


# ------------------------------------------------------------------
# Task profile
# ------------------------------------------------------------------


@dataclass
class TaskProfile:
    raw_text: str
    intent: list[Intent]
    complexity: Complexity
    has_url: bool = False
    has_code: bool = False
    estimated_tokens: int = 0
    confidence: float = 1.0  # classifier self-confidence (0–1)
    notes: list[str] = field(default_factory=list)

    def primary_intent(self) -> Intent:
        return self.intent[0] if self.intent else Intent.UNKNOWN

    def to_dict(self) -> dict:
        return {
            "intent": [i.value for i in self.intent],
            "complexity": self.complexity.value,
            "has_url": self.has_url,
            "has_code": self.has_code,
            "estimated_tokens": self.estimated_tokens,
            "confidence": self.confidence,
            "notes": self.notes,
        }


# ------------------------------------------------------------------
# Heuristic rule sets
# ------------------------------------------------------------------

_URL_RE = re.compile(r"https?://\S+")
_CODE_FENCE_RE = re.compile(r"```")

# (pattern, intent, complexity_hint, score)  — higher score = stronger signal
_INTENT_RULES: list[tuple[re.Pattern, Intent, Complexity | None, float]] = [
    # Research
    (
        re.compile(
            r"\b(research|fetch|scrape|summarize url|look up|find info|search for|google|browse)\b",
            re.I,
        ),
        Intent.RESEARCH,
        Complexity.HYBRID,
        0.8,
    ),
    # Testing
    (
        re.compile(
            r"\b(run tests?|pytest|npm test|failing test|test suite|test runner|ci|check tests?)\b",
            re.I,
        ),
        Intent.TESTING,
        Complexity.LOCAL,
        0.9,
    ),
    # Code fix
    (
        re.compile(
            r"\b(fix|debug|patch|resolve|error|bug|broken|traceback|exception|failing)\b", re.I
        ),
        Intent.CODE_FIX,
        Complexity.FRONTIER,
        0.6,
    ),
    # Code gen
    (
        re.compile(
            r"\b(write|generate|create|implement|build|scaffold|new (script|module|function|class|tool))\b",
            re.I,
        ),
        Intent.CODE_GEN,
        Complexity.FRONTIER,
        0.7,
    ),
    # Embedding / indexing
    (
        re.compile(r"\b(embed|index|chunk|sweep|vector|lancedb|reindex)\b", re.I),
        Intent.EMBED,
        Complexity.LOCAL,
        0.9,
    ),
    # Query / semantic search
    (
        re.compile(
            r"\b(query|search (my|the) (code|knowledge|docs?|codebase)|find in (code|knowledge))\b",
            re.I,
        ),
        Intent.QUERY,
        Complexity.LOCAL,
        0.85,
    ),
    # Summarize
    (
        re.compile(r"\b(summarize|summary|tldr|condense|overview of|brief(ly)?)\b", re.I),
        Intent.SUMMARIZE,
        Complexity.HYBRID,
        0.7,
    ),
]

# Token-count → complexity thresholds (rough)
_TOKEN_FRONTIER_THRESHOLD = 1500  # above this → lean frontier
_TOKEN_AGENT_THRESHOLD = 4000  # above this → consider agent


# ------------------------------------------------------------------
# Classifier
# ------------------------------------------------------------------


class Classifier:
    """
    Rule-based task classifier (v1).

    Produces a TaskProfile by scanning the task description for intent signals,
    estimating token count, and detecting URLs and code blocks.
    """

    def classify(self, task_text: str) -> TaskProfile:
        text = task_text.strip()
        has_url = bool(_URL_RE.search(text))
        has_code = bool(_CODE_FENCE_RE.search(text))
        estimated_tokens = max(1, len(text) // 4)

        # Collect intent votes
        intent_scores: dict[Intent, float] = {}
        complexity_votes: dict[Complexity, float] = {}
        notes: list[str] = []

        for pattern, intent, complexity_hint, score in _INTENT_RULES:
            if pattern.search(text):
                intent_scores[intent] = max(intent_scores.get(intent, 0.0), score)
                if complexity_hint:
                    complexity_votes[complexity_hint] = (
                        complexity_votes.get(complexity_hint, 0.0) + score
                    )

        # URLs always suggest research + hybrid at minimum
        if has_url:
            intent_scores[Intent.RESEARCH] = max(intent_scores.get(Intent.RESEARCH, 0.0), 0.5)
            complexity_votes[Complexity.HYBRID] = complexity_votes.get(Complexity.HYBRID, 0.0) + 0.3
            notes.append("URL detected — research route likely")

        # Code blocks suggest frontier for generation/fix
        if has_code:
            complexity_votes[Complexity.FRONTIER] = (
                complexity_votes.get(Complexity.FRONTIER, 0.0) + 0.4
            )
            notes.append("Code block detected — frontier model preferred")

        # Token count escalations
        if estimated_tokens > _TOKEN_AGENT_THRESHOLD:
            complexity_votes[Complexity.AGENT] = complexity_votes.get(Complexity.AGENT, 0.0) + 0.5
            notes.append(f"Large input (~{estimated_tokens} tokens) — agent tier considered")
        elif estimated_tokens > _TOKEN_FRONTIER_THRESHOLD:
            complexity_votes[Complexity.FRONTIER] = (
                complexity_votes.get(Complexity.FRONTIER, 0.0) + 0.3
            )
            notes.append(f"Medium input (~{estimated_tokens} tokens) — frontier preferred")

        # Sort intents by score descending
        sorted_intents = sorted(intent_scores.items(), key=lambda x: x[1], reverse=True)
        intents = [i for i, _ in sorted_intents] or [Intent.UNKNOWN]

        # Pick complexity
        if complexity_votes:
            complexity = max(complexity_votes, key=complexity_votes.get)
        else:
            complexity = Complexity.LOCAL  # default: try local first

        # Self-confidence: how decisive was the top intent signal?
        top_score = sorted_intents[0][1] if sorted_intents else 0.0
        confidence = min(1.0, top_score)

        return TaskProfile(
            raw_text=text,
            intent=intents,
            complexity=complexity,
            has_url=has_url,
            has_code=has_code,
            estimated_tokens=estimated_tokens,
            confidence=confidence,
            notes=notes,
        )


if __name__ == "__main__":
    clf = Classifier()
    samples = [
        "Run the test suite and show me what's failing",
        "Research how FastMCP handles async tools — https://github.com/modelcontextprotocol",
        "Write a new Python script that chunks markdown files by heading level",
        "Query the local knowledge base for how the dispatcher works",
        "Fix the bug in router/dispatcher.py where it crashes on empty input",
    ]
    for s in samples:
        p = clf.classify(s)
        print(f"\n> {s[:60]}…")
        print(f"  Intent: {[i.value for i in p.intent]}")
        print(f"  Complexity: {p.complexity.value}  Confidence: {p.confidence:.2f}")
        if p.notes:
            print(f"  Notes: {p.notes}")
