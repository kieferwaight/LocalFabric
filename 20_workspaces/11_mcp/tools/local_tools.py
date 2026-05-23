"""Thin MCP-facing exports for internal local workflows and tools."""

from tools.shell.run_tests import run_local_tests
from workflows.research.local import _pick_ollama_model, local_research_scaffold

__all__ = ["_pick_ollama_model", "local_research_scaffold", "run_local_tests"]
