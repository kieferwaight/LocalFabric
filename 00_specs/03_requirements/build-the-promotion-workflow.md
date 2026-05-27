# Requirements — build-the-promotion-workflow

Decisions made from the research stage. The notebook is the deliverable; this
file is the contract it satisfies.

## Functional requirements

### F1 — One notebook, one slug, one promotion run

The notebook accepts a single input variable `SLUG` (e.g. `"my-idea"`) and a
starting stage. Running it from the top promotes the spec from its current
stage to `06_final/`, writing one Markdown file per stage at
`00_specs/0N_<stage>/<slug>.md`.

### F2 — Each stage is its own cell

Stages are not bundled into a single function call. Each stage has at least
two cells: one that shows the prompt being assembled, one that runs the LLM
call and writes the artifact. This is the *observability* promise — the user
can stop after any stage, edit the artifact by hand, and re-enter at the next
stage.

### F3 — Full upstream chain as context

Each stage prompt receives the *full chain* of upstream artifacts as context,
not just the immediately prior stage. (Resolves research Q1.) The chain is
short enough (≤6 stages × ~2 KB) to fit in any local model's context.

### F4 — Stage prompts live under the `spec.promotion.*` namespace

One prompt file per stage, in the flat `12_prompts/` directory:

- `12_prompts/spec.promotion.research.task.md`
- `12_prompts/spec.promotion.requirements.task.md`
- `12_prompts/spec.promotion.tasks.task.md`
- `12_prompts/spec.promotion.prompts.task.md`
- `12_prompts/spec.promotion.final.task.md`

Each is a Jinja-style template with `{{idea}}`, `{{research}}`, etc.
placeholders. Prompts are provider-agnostic per
[12_prompts/README.md](12_prompts/README.md).

### F5 — `06_final/` produces a bundle plus an index

(Resolves research Q2.) `06_final/<slug>.md` contains:

1. A frozen, agent-ready prompt suitable for `claude_<type>_<slug>` work.
1. An index section linking each upstream stage artifact by relative path.

The frozen prompt is what a coding agent receives — it should reference the
upstream artifacts rather than inlining them, because the upstream artifacts
are the source of truth.

### F6 — Overwrite with a confirmation cell

(Resolves research Q3.) Re-running a stage overwrites the artifact. A
dedicated cell named `CONFIRM_OVERWRITE` must be uncommented to authorize
overwriting an existing artifact. Default behavior on existing artifact is to
raise.

### F7 — Per-stage `_meta.yaml`

(Resolves research Q4.) Alongside `<slug>.md` in each stage folder, the
notebook writes `<slug>.meta.yaml` with: `model`, `provider`, `prompt_path`,
`prompt_sha256`, `promoted_at` (ISO-8601, UTC).

## Non-functional requirements

### N1 — LLM backend is configurable, defaults to LM Studio

The notebook reads `LMSTUDIO_HOST` (default `http://localhost:1234/v1`) and a
`MODEL` constant. No code path hardcodes a single provider — the same notebook
must run against Ollama by changing two constants.

### N2 — Classification-audit clean

The notebook lives in [20_notebooks/](20_notebooks), is not
imported by other buckets, and contains no business logic that other buckets
would need. When a workflow under [06_workflows/](06_workflows)
later supersedes the notebook, file I/O moves into a driver and LLM calls
move into a harness — see [04_tasks/build-the-promotion-workflow.md](00_specs/04_tasks/build-the-promotion-workflow.md)
for the migration path.

### N3 — Path discipline

The notebook resolves the spec tree via `core.paths.REPO_ROOT`, not via
`__file__` arithmetic. If `core.paths` doesn't yet expose a `specs_root()`
helper, the notebook composes the path locally from `REPO_ROOT` rather
than introducing a parallel anchor.

### N4 — No new install required to read the artifacts

The artifacts are plain Markdown. The notebook needs only `openai` and `pyyaml`
to run; both should be in the `dev` extra of
[pyproject.toml](pyproject.toml).

## Acceptance criteria

A1. Running the notebook end-to-end with `SLUG = "build-the-promotion-workflow"`
against this very spec produces files identical-in-shape to the ones
Claude wrote by hand (content will differ — that is expected).

A2. Listing `find 00_specs -name "build-the-promotion-workflow*"`
after a successful run shows: one Markdown file in each of
`01_ideas/` through `06_final/`, plus one `.meta.yaml` in each of
`02_research/` through `06_final/`.

A3. Re-running a stage without uncommenting `CONFIRM_OVERWRITE` raises.

A4. `python3 17_scripts/audit_classifications.py` reports no new findings.

A5. The frozen prompt in `06_final/<slug>.md` is self-contained enough that
pasting it into a fresh agent session, plus the linked upstream
artifacts, is sufficient to start the implementation branch.

## Out of scope

- Exposing `/promote-spec` as a slash command, MCP tool, or pre-commit hook.
  Those are downstream uses of the same prompts and are tracked as follow-ups
  in [04_tasks/build-the-promotion-workflow.md](00_specs/04_tasks/build-the-promotion-workflow.md).
- Automating idea *capture* (e.g. converting Slack messages into ideas).
- Tests against a real LLM — the notebook is the test surface for now.
