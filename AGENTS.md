# AGENTS.md — LocalFabric

Navigation contract for AI agents (Claude, Codex, Copilot, Gemini, etc.) working in this repo. Read it before running anything. The org-level conventions in [`~/src/AGENTS.md`](../AGENTS.md) still apply on top of these.

## uv is the primary Python interface

All Python work in this repo goes through [uv](https://docs.astral.sh/uv/). Do not invoke bare `pip`, `python`, or `python3` to operate the project; do not create venvs by hand. uv is the single source of truth for the interpreter, lockfile, and dependency groups.

### Canonical commands

| Task | Command |
| --- | --- |
| Install base + dev tooling | `uv sync --extra dev` |
| Enable cloud / LM Studio providers | `uv sync --extra llm` |
| Add a dependency | `uv add <pkg>` (or `uv add --optional <group> <pkg>`) |
| Run a one-off script | `uv run python path/to/script.py` |
| Run a console entry | `uv run localfabric --help` (also `localfabric-md`, `localfabric-mcp`, `localfabric-api`) |
| Run the test suite | `uv run pytest` |
| Run a YAML workflow | `uv run python 02_core/runtimes/yaml/interpreter.py <file> <def-id>` |
| Run a markdown prompt | `uv run localfabric-md <file>.md [--key=value]` |

### Why uv

- Single resolver across base deps and every optional-dependency group declared in [`pyproject.toml`](pyproject.toml).
- `uv run` automatically activates `.venv/` for the spawned process, which matters because the YAML runtime dispatches `python` subprocess blocks under the parent interpreter (`sys.executable`) — invoking via uv guarantees those subprocesses see the editable bucket-aliases install.
- One command for everything, instead of `python -m venv` + `pip install` + manual activation.

### When you see a non-uv command in older docs

Treat it as legacy. Replace `pip install -e .` with `uv sync`, `python -m pytest` with `uv run pytest`, etc. If you find such a command in a checked-in file, update it.

## Optional-dependency groups

Declared in [`pyproject.toml`](pyproject.toml), surfaced in [README.md](README.md). The README table is regenerated; treat `pyproject.toml` as authoritative. Common combinations:

- `uv sync --extra dev` — pytest, ruff, mypy, formatters, pre-commit.
- `uv sync --extra llm` — anthropic, openai, google-generativeai (needed for the Claude / OpenAI / Codex / LM Studio harnesses).
- `uv sync --extra vision` — opencv, pytesseract.
- `uv sync --extra pdf` — pymupdf, pdfminer, pdf2image.
- `uv sync --extra vector` — lancedb.

Combine with commas: `uv sync --extra dev --extra llm --extra vision`.

## Cross-references

- [README.md](README.md) — repo identity, bucket map, console scripts, optional-dependency table (all regenerated).
- [`~/src/AGENTS.md`](../AGENTS.md) — org-level conventions across `~/src`.
- `~/.claude/CLAUDE.md` (per-user) — CodeGraph usage rules; CodeGraph is the primary symbol-lookup tool in this repo.
