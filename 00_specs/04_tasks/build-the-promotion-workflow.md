# Tasks — build-the-promotion-workflow

Work items derived from [03_requirements/build-the-promotion-workflow.md](00_specs/03_requirements/build-the-promotion-workflow.md).
Each task is scoped to a single bucket so it passes the classification audit
and can be picked up as an independent branch.

## T1 — Write per-stage promotion prompts

**Bucket:** `12_prompts`

Add five prompt templates in the flat `12_prompts/` directory under the
`spec.promotion.*` namespace:

- `spec.promotion.research.task.md` — given an idea, produce a survey of
  repo assets that bear on the idea and surface open questions for
  requirements.
- `spec.promotion.requirements.task.md` — given idea + research, produce
  functional and non-functional requirements plus acceptance criteria.
- `spec.promotion.tasks.task.md` — given idea + research + requirements,
  produce a bucketed task list.
- `spec.promotion.prompts.task.md` — given the full chain, produce
  agent-ready prompts for each task.
- `spec.promotion.final.task.md` — given the full chain, produce the
  frozen handoff prompt plus an index.

Each template uses Jinja-style `{{idea}}`, `{{research}}`, `{{requirements}}`,
`{{tasks}}`, `{{prompts}}` placeholders, and contains no provider-specific
instructions.

**Acceptance:** prompts render with `string.Template` or Jinja in the
notebook without errors.

## T2 — Add `openai`, `pyyaml` to dev extra

**Bucket:** root `pyproject.toml`

Confirm `[project.optional-dependencies].dev` in
[pyproject.toml](pyproject.toml) includes both
packages. Add them if missing.

**Acceptance:** `pip install -e ".[dev]"` succeeds and `import openai, yaml`
works inside the notebook.

## T3 — Build `promote_spec.ipynb`

**Bucket:** `20_notebooks`

Implement the notebook per F1–F7 of the requirements. Cell layout:

1. Constants (`SLUG`, `START_STAGE`, `MODEL`, `LMSTUDIO_HOST`).
1. Path resolution via `core.paths.REPO_ROOT`.
1. Stage definitions (ordered list of `(folder, prompt_path, output_var)`).
1. Helper: `read_chain(slug)` — returns dict of upstream artifacts present.
1. Helper: `render_prompt(template_path, chain)` — Jinja render.
1. Helper: `call_llm(prompt, model, host)` — OpenAI-compatible chat call.
1. Helper: `write_stage(slug, stage, content, meta)` — writes
   `<slug>.md` and `<slug>.meta.yaml`, raises on existing unless
   `CONFIRM_OVERWRITE` truthy.
1. One **prompt-preview cell + run cell** per stage from `START_STAGE`
   onward.
1. Final cell that prints the resulting `06_final/<slug>.md` for the user
   to inspect.

**Acceptance:** A1, A2, A3 from the requirements.

## T4 — Add LM Studio model entry (optional, deferred)

**Bucket:** `13_models`

If the user wants to standardize on a specific LM Studio model (e.g.
`qwen3.6-27b` from the format-markdown idea), register it in
[13_models/registry.yaml](13_models/registry.yaml) and add a
README under `13_models/local/<model>/`. Not required for the first
notebook run — the notebook accepts any chat-capable model string.

**Acceptance:** `python3 17_scripts/audit_classifications.py` reports no
findings related to registry/configuration drift.

## T5 — Migration path to workflow + MCP exposure (follow-up, not this PR)

**Bucket:** `06_workflows`, `11_mcp`, `03_adapters/cli`

Document, but do not implement here: the migration that moves the notebook's
orchestration into a workflow under `06_workflows/spec_promotion/`, with
file I/O delegated to a driver and LLM calls delegated to a harness. Once
that exists, the same capability is exposed by a CLI adapter and an MCP
tool. The notebook stays as the *exploratory* surface.

**Acceptance:** N/A for this PR. Tracked as the next idea to drop in
`01_ideas/`.

## Suggested branch sequence

1. `claude_feature_spec-promotion-prompts` — T1, T2.
1. `claude_feature_spec-promotion-notebook` — T3 (depends on 1).
1. `claude_chore_register-lmstudio-model` — T4 (optional, parallel).
1. Follow-up idea for T5 dropped after notebook is observed working.
