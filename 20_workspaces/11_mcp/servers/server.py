"""
server.py — FastMCP server exposing local router tools.

Tools exposed:
    local_router_research       — fetch + Ollama-summarize a URL or search topic
    local_router_run_tests      — execute a shell test command, return trimmed output
    local_router_query_knowledge — semantic search over the indexed project codebase
    local_router_sweep_index    — re-index the project directory into the vector store

Run directly (stdio transport for Claude Desktop):
    python -m mcp.servers.server

Install dependencies first:
    pip install mcp ollama requests beautifulsoup4 lancedb numpy
"""

import os
import sys

# Ensure project root is on the path when run as a module
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from typing import Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, ConfigDict

from mcp_layer.servers.config import SERVER_NAME, EMBED_MODEL, VECTOR_STORE_PATH
from mcp_layer.tools.local_tools import local_research_scaffold, run_local_tests

# ------------------------------------------------------------------
# Server init
# ------------------------------------------------------------------

mcp = FastMCP(SERVER_NAME)

# ------------------------------------------------------------------
# Lazy singletons — avoid import errors at startup if optional deps missing
# ------------------------------------------------------------------

_knowledge_query = None


def _get_knowledge_query():
    global _knowledge_query
    if _knowledge_query is None:
        from tools.embeddings.query import LocalKnowledgeQuery
        _knowledge_query = LocalKnowledgeQuery(
            backend="lancedb",
            store_path=VECTOR_STORE_PATH,
            model=EMBED_MODEL,
        )
    return _knowledge_query


# ------------------------------------------------------------------
# Input models
# ------------------------------------------------------------------

class ResearchInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    topic_or_url: str = Field(
        ...,
        description="A URL to fetch and summarize, or a plain-text topic to search via DuckDuckGo Lite.",
        min_length=3,
        max_length=500,
    )


class RunTestsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    command: str = Field(
        default="pytest",
        description="Shell command to run (e.g. 'pytest', 'pytest tests/unit', 'npm test'). "
                    "Runs in the project root directory with a 30-second timeout.",
        max_length=500,
    )


class QueryKnowledgeInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    query: str = Field(
        ...,
        description="Natural-language question or task description to search for in the local codebase.",
        min_length=3,
        max_length=500,
    )
    k: int = Field(
        default=5,
        description="Number of top results to return (1–10).",
        ge=1,
        le=10,
    )
    source_filter: Optional[str] = Field(
        default=None,
        description="Optional: restrict results to chunks from a specific file path.",
    )


class SweepIndexInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    target_dir: Optional[str] = Field(
        default=None,
        description="Directory to index. Defaults to the project root. "
                    "Must be an absolute path on the local machine.",
    )
    force: bool = Field(
        default=False,
        description="If true, re-embed all files even if unchanged.",
    )
    clear: bool = Field(
        default=False,
        description="If true, drop the entire vector store and rebuild from scratch.",
    )


# ------------------------------------------------------------------
# Tools
# ------------------------------------------------------------------

@mcp.tool(
    name="local_router_research",
    annotations={
        "title": "Local Research (Ollama)",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def local_router_research(params: ResearchInput) -> str:
    """
    Fetch and summarize a URL or search topic using a local Ollama model (zero cloud cost).

    For a URL: fetches the page, strips HTML, and summarizes with nomic/qwen2.5/llama3.
    For a topic: searches DuckDuckGo Lite and summarizes the results.

    Use this before routing to a frontier model to pre-process research cheaply.

    Args:
        params.topic_or_url: URL or plain-text search topic.

    Returns:
        str: Markdown-formatted summary, or cleaned raw text if Ollama is unavailable.
    """
    return local_research_scaffold(params.topic_or_url)


@mcp.tool(
    name="local_router_run_tests",
    annotations={
        "title": "Run Local Tests",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
async def local_router_run_tests(params: RunTestsInput) -> str:
    """
    Execute a local test suite and return a trimmed, context-window-friendly result.

    On success: returns the last 500 chars of stdout.
    On failure: returns the last 30 lines of stderr/stdout (to avoid flooding context windows).
    Times out after 30 seconds.

    Args:
        params.command: Shell command to run (default: "pytest").

    Returns:
        str: SUCCESS or FAILURE with trimmed log output.
    """
    return run_local_tests(params.command)


@mcp.tool(
    name="local_router_query_knowledge",
    annotations={
        "title": "Query Local Knowledge Base",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def local_router_query_knowledge(params: QueryKnowledgeInput) -> str:
    """
    Semantically search the indexed project codebase and return the most relevant chunks
    as a formatted markdown context block ready to inject into a prompt.

    The knowledge base must be populated first via local_router_sweep_index.

    Args:
        params.query:         Natural-language question or task description.
        params.k:             Number of results (1–10, default 5).
        params.source_filter: Optional file path to restrict results to.

    Returns:
        str: Markdown context block with top-k relevant code/text excerpts.
    """
    try:
        lkq = _get_knowledge_query()
    except ImportError as exc:
        return f"Knowledge query unavailable — missing dependency: {exc}\nRun: pip install lancedb numpy ollama"

    return lkq.query(
        query_text=params.query,
        k=params.k,
        source_filter=params.source_filter,
        as_markdown=True,
    )


@mcp.tool(
    name="local_router_sweep_index",
    annotations={
        "title": "Sweep and Index Project",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def local_router_sweep_index(params: SweepIndexInput) -> str:
    """
    Walk the project directory, chunk all source files, generate embeddings via Ollama,
    and persist them to the local LanceDB vector store.

    Only re-processes files that have changed since the last sweep (MD5 dirty-check).
    Ollama must be running locally for this to work.

    Args:
        params.target_dir: Directory to sweep (default: project root).
        params.force:      Re-embed all files even if unchanged.
        params.clear:      Drop and rebuild the entire store.

    Returns:
        str: Summary of files scanned, chunks added, and elapsed time.
    """
    try:
        from tools.embeddings.sweep import sweep
    except ImportError as exc:
        return f"Sweep unavailable — missing dependency: {exc}\nRun: pip install lancedb numpy ollama"

    target = params.target_dir or _PROJECT_ROOT
    stats = sweep(
        target_dir=target,
        dry_run=False,
        force=params.force,
        clear=params.clear,
        verbose=False,
    )

    return (
        f"Sweep complete.\n"
        f"  Files scanned : {stats['files_scanned']}\n"
        f"  Files changed : {stats['files_changed']}\n"
        f"  Chunks added  : {stats['chunks_added']}\n"
        f"  Skipped       : {stats['skipped']}\n"
        f"  Errors        : {stats['errors']}\n"
        f"  Elapsed       : {stats['elapsed_sec']}s"
    )


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
