"""
mcp.tools — zero-cost local pre-processing tools backed by Ollama.

Exposes:
    local_research_scaffold(topic_or_url) — fetch + summarize via local model
    run_local_tests(command)              — execute a shell command with trimmed output
"""

from .local_tools import local_research_scaffold, run_local_tests

__all__ = ["local_research_scaffold", "run_local_tests"]
