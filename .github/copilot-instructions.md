# Copilot Instructions for LocalFabric

## Build, Test, and Lint Commands

- **Build/install:**
  - `pip install -e .` (from the root; uses `pyproject.toml`)
- **Run all tests:**
  - `pytest` (from root or `20_workspaces`)
- **Run a single test:**
  - `pytest -k <pattern>` or `python -m pytest <test_file>`
- **Lint:**
  - `ruff .` (configured in `pyproject.toml`)
- **Type check:**
  - `mypy .`

## CLI Entrypoint

- Main CLI: `python -m 20_workspaces.03_adapters.cli.main [COMMAND]`
- Available subcommands:
  - `markdown format` — Format markdown files using LM Studio
  - `db init` — Initialize the SQLite database
  - `ingest run` — Ingest assets from a source folder
  - `image-intelligence run` — Run image intelligence pipeline on a collection
  - `image-intelligence single` — Run image intelligence on a single image

## Architecture & Structure

- Numeric-prefixed top-level buckets carry import order; import aliases are registered in `conftest.py` + `pyproject.toml`'s `[tool.setuptools.package-dir]`.
- Tests are in `16_tests/`.
- The MCP server lives at `02_core/interfaces/mcp/` (registered as `core.interfaces.mcp`).

## Key Conventions

- Use clean import names (numeric prefixes are not used in imports).
- All test, lint, and build commands are Python-based (no Makefile or shell runners).
- Use `pytest` for all test discovery and execution.
- Use `ruff` and `mypy` for linting and type checking.
- For workspace-specific details, see `20_workspaces/README.md`.

## Additional Notes

- No other AI assistant config files (Claude, Cursor, etc.) are present.
- If you need to validate service compose configs, use `python3 -m pytest 20_workspaces/16_tests/test_compose_configs.py`.
- For further details, consult `README.md` and workspace documentation.
