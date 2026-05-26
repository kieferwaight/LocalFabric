# local-ollama-tools

Two zero-token-cost local routines for use as a pre-processing layer in front of paid frontier models. Built to be wrapped by an MCP server later.

- `local_research_scaffold(topic_or_url)` — fetches a page (or runs a DuckDuckGo lite search for a topic), strips it to readable text, and summarizes via the first available local Ollama model.
- `run_local_tests(command)` — runs a shell command (default `pytest`) with a 30 s timeout and returns either a `SUCCESS` trailer or a tail-trimmed `FAILURE` log (last 30 lines), keeping cloud context windows tight.

## Install

```bash
pip install -r requirements.txt
ollama pull qwen2.5:7b   # or any chat-capable model; the loader auto-picks the first available
```

Ollama must be running locally (`ollama serve`). If Ollama is unreachable, `local_research_scaffold` falls back to returning the cleaned raw text extract instead of crashing.

## Usage

```python
from mcp_servers.tools.local_tools import local_research_scaffold, run_local_tests

print(local_research_scaffold("https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/main/README.md"))
print(local_research_scaffold("mcp python sdk quickstart"))   # topic - DuckDuckGo lite fallback
print(run_local_tests("pytest -k smoke"))
```

## Tests

```bash
python3 16_tests/local_ollama_tools/test_runner.py            # end-to-end smoke
python3 -m pytest 16_tests/local_ollama_tools/test_local_tools.py -v
```

The Ollama summary test is marked `xfail(strict=False)` so it is skipped gracefully when no local model is available.

## Model selection

`_pick_ollama_model()` queries `ollama.list()` and prefers, in order: `qwen2.5:7b`, any `qwen2.5*`, then `llama3*`. Falls back to the first model returned by the server.
