# Final — build-the-promotion-workflow

This is the frozen handoff artifact for the
`build-the-promotion-workflow` spec. It bundles the agent-ready prompt with
an index of upstream artifacts. The upstream files are the source of truth;
this file may be regenerated.

## Stage index

| Stage | Artifact |
|---|---|
| Idea | [01_ideas/build-the-promotion-workflow.md](20_workspaces/00_specs/01_ideas/build-the-promotion-workflow.md) |
| Research | [02_research/build-the-promotion-workflow.md](20_workspaces/00_specs/02_research/build-the-promotion-workflow.md) |
| Requirements | [03_requirements/build-the-promotion-workflow.md](20_workspaces/00_specs/03_requirements/build-the-promotion-workflow.md) |
| Tasks | [04_tasks/build-the-promotion-workflow.md](20_workspaces/00_specs/04_tasks/build-the-promotion-workflow.md) |
| Prompts | [05_prompts/build-the-promotion-workflow.md](20_workspaces/00_specs/05_prompts/build-the-promotion-workflow.md) |

## Frozen handoff prompt

Paste the block below into a fresh agent session. The agent must read the
linked upstream artifacts before doing anything else.

---

> You are working in the `~/agents/claude/LocalFabric` worktree. Read
> [CLAUDE.md](CLAUDE.md) for repository conventions and
> [.github/PULL_REQUEST_TEMPLATE.md](.github/PULL_REQUEST_TEMPLATE.md) for PR
> shape before you start.
>
> Your assignment is to build the spec-promotion workflow described in
> `20_workspaces/00_specs/01_ideas/build-the-promotion-workflow.md` and
> refined in the artifacts indexed at the top of this file. The first
> trigger of this capability is a Jupyter notebook —
> `20_workspaces/15_notebooks/promote_spec.ipynb` — that promotes a spec
> through `01_ideas/ → 02_research/ → 03_requirements/ → 04_tasks/ →
> 05_prompts/ → 06_final/` by calling a local OpenAI-compatible chat model
> at each stage.
>
> Implement the three branchable units in this order:
>
> 1. `claude_feature_spec-promotion-prompts` — create the five per-stage
>    prompt templates under
>    `20_workspaces/12_prompts/tasks/spec_promotion/` as specified in P1
>    of the prompts stage. Use the hand-written upstream artifacts of
>    this very spec as worked examples — the prompts should produce
>    artifacts of the same shape.
>
> 2. `claude_feature_spec-promotion-notebook` — implement
>    `20_workspaces/15_notebooks/promote_spec.ipynb` per the cell layout in
>    T3 of the tasks stage, satisfying acceptance criteria A1–A5 of the
>    requirements stage. Path resolution must go through
>    `core.paths.WORKSPACES_ROOT`. Provider is LM Studio by default
>    (`http://localhost:1234/v1`); model is a top-of-notebook constant.
>
> 3. Validate by promoting a fresh dummy spec (drop a short idea in
>    `01_ideas/demo-spec.md`, run the notebook with `SLUG = "demo-spec"`)
>    and pasting the resulting `find 20_workspaces/00_specs -name
>    "demo-spec*"` output into the PR description.
>
> Constraints that override defaults:
>
> - Do not move orchestration into `06_workflows/` in this PR. The notebook
>   is intentionally the only execution surface for the first iteration.
> - Do not expose any of this as a slash command, MCP tool, or CLI adapter
>   in this PR. Those are separate ideas to be promoted later.
> - Do not introduce new top-level dependencies; reuse `openai` and
>   `pyyaml` from the `dev` extra.
> - The notebook's helper functions live in the notebook itself, not in a
>   shared module — keep this as a sandbox capability until usage justifies
>   promotion to a bucketed workflow.
>
> Definition of done:
>
> - All five prompt templates exist and render without error.
> - `promote_spec.ipynb` runs end-to-end against a real local model and
>   produces one Markdown artifact per stage plus a `.meta.yaml` sidecar
>   from stage 02 onward.
> - `python3 17_scripts/audit_classifications.py` reports no new findings.
> - The PR uses the
>   [.github/PULL_REQUEST_TEMPLATE.md](.github/PULL_REQUEST_TEMPLATE.md)
>   fields, with the Assigned Prompt set to the contents of this file's
>   "Frozen handoff prompt" section.

---

## Follow-up ideas to drop into `01_ideas/` after this ships

- `expose-promotion-workflow.md` — move orchestration into
  `06_workflows/spec_promotion/`, expose via `03_adapters/cli` and
  `11_mcp`.
- `promote-on-commit.md` — pre-commit hook that auto-promotes any new file
  in `01_ideas/` through `02_research/` for review-time triage.
