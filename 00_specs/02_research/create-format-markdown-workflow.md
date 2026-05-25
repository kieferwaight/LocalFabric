---
model: qwen/qwen3.6-27b
provider: lmstudio
endpoint: http://localhost:1234/v1
prompt_path: 12_prompts/tasks/spec_promotion/02_research.md
prompt_sha256: 380877ce7d51024e87d3ef078a3d0bb73f1fafb54fae883bb62dac6e2b7934dd
promoted_at: '2026-05-23T19:06:13Z'
---

# Research — notebook-format-markdown-test

## Existing Repository Assets
- `20_workspaces/15_notebooks/` — Target directory for the new notebook; existing notebook templates or execution conventions should be reused.
- `20_workspaces/12_prompts/tasks/format-markdown.md` — The prompt artifact to be consumed and tested; must be read as-is without modification.
- `08_drivers/` or `03_adapters/` — Likely contains existing LLM client implementations (e.g., OpenAI-compatible API wrappers) that should be reused for LM Studio communication.
- `04_harnesses/` or `06_workflows/` — Existing orchestration harnesses or workflow definitions that may provide reusable step-chaining, logging, or evaluation utilities.
- `02_core/` — Core configuration, environment variable handling, or prompt-loading utilities that the notebook should leverage instead of hardcoding paths or credentials.

## Layer-Ownership Constraints
- `12_prompts`: The notebook must treat `format-markdown.md` as an immutable input artifact. Prompt versioning, templating, or fallback logic belongs to the prompt layer, not the notebook.
- `03_adapters` / `08_drivers`: All HTTP/model calls must route through existing adapter/driver abstractions. Direct `requests` or raw API calls in the notebook are discouraged to maintain consistency with the orchestration layer.
- `04_harnesses` / `06_workflows`: The notebook should be structured as a standalone test unit initially, but its input/output schema must align with harness/workflow step contracts to enable future pipeline integration.
- `11_mcp`: MCP dispatch logic, tool registration, and server routing are out of scope for this notebook. Any future MCP integration must be abstracted behind a driver or workflow step.
- `02_core`: Configuration (base URL, model name, context limits, API keys) must be sourced from core config/env patterns rather than hardcoded in the notebook cells.

## External Dependencies
- LM Studio local server (`http://localhost:1234/v1`) exposing an OpenAI-compatible chat completions endpoint.
- Model: `qwen/qwen3.6-27b` (or equivalent Qwen 3.6 27B variant) loaded in LM Studio.
- Context window capacity: Minimum 10k tokens, target 18k tokens for the model/server configuration.
- Python/Jupyter execution environment with standard notebook dependencies (e.g., `ipykernel`, `requests`/`openai` client, markdown parsing utilities).
- OpenAI API specification v1 for request/response payload structure.

## Open Questions for Requirements Stage
1. How should the notebook load and version the `format-markdown.md` prompt? (Hypothesis: Use an existing prompt registry/loader from `02_core` rather than raw file I/O.)
2. Which existing driver or adapter should handle the LM Studio API calls, and what is its expected initialization pattern? (Hypothesis: Reuse an OpenAI-compatible driver already defined in `08_drivers` or `03_adapters`.)
3. How should context/token limits be validated and enforced before sending requests? (Hypothesis: Add a pre-flight token counter that warns or truncates if input exceeds 10k–18k tokens.)
4. What is the expected input format for the notebook test? (Hypothesis: Accept raw string input, file path, or both, with a clear cell for pasting "dirty" markdown.)
5. How should output formatting quality be evaluated or logged? (Hypothesis: Include optional diff/comparison cells or basic heuristic checks for heading consistency, list formatting, and code block syntax.)
6. What abstraction should be used to prepare the notebook for future integration with slash commands, MCP dispatch, and pre-commit hooks? (Hypothesis: Define a reusable `run_format_markdown()` function with a stable signature that can be imported by workflows or drivers.)
7. How should model availability and fallback be handled if `qwen/qwen3.6-27b` is not loaded or fails to respond? (Hypothesis: Require explicit model verification at notebook startup, with clear error messaging rather than silent fallback.)
8. Should the notebook include configuration overrides for temperature, top_p, or other generation parameters, or should those be fixed for deterministic testing? (Hypothesis: Fix generation parameters for reproducibility, with optional toggle cells for experimentation.)