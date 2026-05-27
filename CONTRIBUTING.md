# Contributing to LocalFabric

## Setup

`uv` is the primary Python interface — see [`AGENTS.md`](AGENTS.md). Install:

```
uv sync --extra dev
```

For cloud / LM Studio providers add `--extra llm`; combine extras as needed (e.g. `uv sync --extra dev --extra llm`).

## Branch naming

Use `<provider>_<type>_<short-description>` (e.g. `claude_feature_image-workflow`, `claude_chore_makefile-cleanup`). The PR template checklist and recent merged PRs are the source of truth.

## Workflow

1. Create a branch off `main` following the naming convention above.
1. Make changes — keep the scope of one PR to one logical unit.
1. Format + lint: `make format lint`.
1. Test: `uv run pytest`.
1. Architecture audit: `make audit`. Findings land in `14_data/runs/classification_audit/`.
1. Open a PR. The merge requires a clean audit.

## Commit messages

Imperative summary line, "why" over "what" in the body. End with `Co-Authored-By: ...` if AI-assisted (see recent commits for the exact line).

## Available `make` targets

| Target              | What it does                                                     |
| ------------------- | ---------------------------------------------------------------- |
| `make format`       | Auto-format Python, YAML, and Markdown (ruff, yamlfix, mdformat) |
| `make format-check` | Check formatting without writing (CI mode)                       |
| `make lint`         | Lint Python + YAML (ruff check, yamllint); read-only             |
| `make lint-fix`     | Lint with autofix where supported                                |
| `make audit`        | Run the classification-boundary audit workflow                   |
| `make install-dev`  | `uv sync --extra dev`                                            |
| `make install-all`  | `uv sync --all-extras`                                           |
| `make reset`        | Full rebuild: clean + venv + install-all                         |

Run `make help` for the full list.
