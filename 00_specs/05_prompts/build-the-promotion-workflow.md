# Prompts — build-the-promotion-workflow

Agent-ready prompts, one per task in
[04_tasks/build-the-promotion-workflow.md](00_specs/04_tasks/build-the-promotion-workflow.md).
Each prompt assumes the agent has read the linked upstream artifacts before
starting and is prepared to follow [CLAUDE.md](CLAUDE.md)'s branch/PR rules.

---

## P1 — Write per-stage promotion prompts

**Branch:** `claude_feature_spec-promotion-prompts`

You are implementing T1 from
`00_specs/04_tasks/build-the-promotion-workflow.md`.

Create five files under `12_prompts/tasks/spec_promotion/`:
`02_research.md`, `03_requirements.md`, `04_tasks.md`, `05_prompts.md`,
`06_final.md`.

Each prompt:

- Is a Jinja-style template with placeholders that match the stage's
  upstream chain. Stage `02_research` uses `{{idea}}`. Stage `03_requirements`
  uses `{{idea}}` and `{{research}}`. And so on through `06_final` which uses
  all five upstream variables.
- Begins with a one-line role assignment ("You are a spec promotion
  assistant…") and a numbered task list that mirrors the structure of the
  hand-written `00_specs/0N_<stage>/build-the-promotion-workflow.md` files in
  this repo — those are your worked examples.
- Ends with a strict output-shape instruction ("Return only the Markdown
  body, starting with `# <Stage> — <slug>`. Do not wrap in code fences.").
- Is provider-agnostic. No "you are running on LM Studio" etc.

Acceptance: when these prompts are rendered with the `01_ideas/`
`build-the-promotion-workflow.md` content and run against a 7B-class local
model, the model produces a research-stage artifact that names at least
[REPO_STRUCTURE.md](REPO_STRUCTURE.md), [12_prompts/](12_prompts)
and [13_models/registry.yaml](13_models/registry.yaml).

Do not modify any code in `02_core` through `11_mcp` for this branch.

---

## P2 — Confirm dev dependencies

**Branch:** folded into P1 or `claude_chore_spec-promotion-deps`

You are implementing T2.

In [pyproject.toml](pyproject.toml), confirm
`openai` and `pyyaml` are present in `[project.optional-dependencies].dev`.
If either is missing, add it with no version pin (the lockfile, if any,
governs versions).

Validate by running `pip install -e ".[dev]"` from the repo root and
`python -c "import openai, yaml"`.

---

## P3 — Build `promote_spec.ipynb`

**Branch:** `claude_feature_spec-promotion-notebook`

You are implementing T3 from
`00_specs/04_tasks/build-the-promotion-workflow.md` and must
satisfy F1–F7 plus acceptance A1–A5 from
`00_specs/03_requirements/build-the-promotion-workflow.md`.

The notebook must use the cell layout listed in T3 verbatim — including a
preview cell + run cell pair per stage. Helper functions live in the notebook
itself; do not add a Python module under another bucket.

Path resolution: `from core.paths import REPO_ROOT`, then derive
`SPECS_ROOT = REPO_ROOT / "00_specs"`. Do not climb `__file__`.

LLM call: use the `openai` client pointed at `LMSTUDIO_HOST` (default
`http://localhost:1234/v1`) with `api_key="not-needed"`. Model name is read
from a constant cell at the top.

Validation: after committing, run the notebook end-to-end against a fresh
slug `demo-spec` (drop a 3-sentence idea file in `01_ideas/`). Confirm A2
by running the `find` command and pasting the output into the PR description.

Reminder: you are operating in the `~/agents/claude/LocalFabric` worktree
only.

---

## P4 — (Deferred) Register LM Studio model

**Branch:** `claude_chore_register-lmstudio-model`

Only do this if the user explicitly requests it. Pattern: copy any existing
entry in [13_models/registry.yaml](13_models/registry.yaml),
flip `provider` to `lmstudio`, add a stub README under `13_models/local/`.
Confirm the classification audit stays clean.

---

## P5 — (Deferred) Workflow + MCP exposure

Do not start until the notebook has been observed working by the user and
they explicitly ask for the next stage. The migration shape is described in
T5; the corresponding idea file should be dropped into `01_ideas/` before
opening branches.
