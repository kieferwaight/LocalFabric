"""
config.py — Configuration and Claude Desktop registration helper.

Run this file directly to print the JSON block you need to add to
~/Library/Application Support/Claude/claude_desktop_config.json:

    python -m mcp_layer.servers.config
"""

import json
import os
import sys

# Path to 20_workspaces/ (which carries the import-name symlinks that map
# `mcp_layer`, `tools`, `drivers`, etc. to their numbered bucket dirs).
# `__file__` is 20_workspaces/11_mcp/servers/config.py → go up two levels.
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# ------------------------------------------------------------------
# Server config
# ------------------------------------------------------------------

SERVER_NAME = "local_router_mcp"
SERVER_VERSION = "0.1.0"

# Ollama model preferences (used across tools)
EMBED_MODEL = "nomic-embed-text"
CHAT_MODEL_PREFERENCE = ("qwen2.5:7b", "qwen2.5", "llama3", "llama3.2", "llama3.1")

# LanceDB store path
VECTOR_STORE_PATH = os.path.expanduser("~/.local_router_vectors")

# Embedder cache path
EMBED_CACHE_PATH = os.path.expanduser("~/.local_router_cache/embed_cache.json")

# ------------------------------------------------------------------
# Claude Desktop config snippet
# ------------------------------------------------------------------

def _python_executable() -> str:
    """Return the current Python interpreter path."""
    return sys.executable


def claude_desktop_entry() -> dict:
    """Return the mcpServers entry for claude_desktop_config.json."""
    return {
        "local_router": {
            "command": _python_executable(),
            "args": ["-m", "mcp_layer.servers.server"],
            "cwd": _PROJECT_ROOT,
            "env": {
                "PYTHONPATH": _PROJECT_ROOT,
            },
        }
    }


def _config_path() -> str:
    if sys.platform == "darwin":
        return os.path.expanduser(
            "~/Library/Application Support/Claude/claude_desktop_config.json"
        )
    elif sys.platform == "win32":
        return os.path.join(os.environ.get("APPDATA", ""), "Claude", "claude_desktop_config.json")
    else:
        return os.path.expanduser("~/.config/claude/claude_desktop_config.json")


def print_registration_instructions() -> None:
    entry = claude_desktop_entry()
    config_path = _config_path()

    print("\n" + "=" * 60)
    print("Claude Desktop Registration")
    print("=" * 60)
    print(f"\n1. Open: {config_path}")
    print("\n2. Add this block inside the top-level 'mcpServers' object:\n")
    print(json.dumps(entry, indent=2))
    print("\n3. Save the file and restart Claude Desktop.")
    print("\nIf claude_desktop_config.json doesn't exist, create it with:")
    print(json.dumps({"mcpServers": entry}, indent=2))
    print("=" * 60 + "\n")


if __name__ == "__main__":
    print_registration_instructions()
