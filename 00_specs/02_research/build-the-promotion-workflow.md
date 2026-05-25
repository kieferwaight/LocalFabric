# Research — build-the-promotion-workflow

Survey of what already exists in the repo that this spec must reuse or
respect. Findings only; decisions move to `03_requirements/`.

## Pipeline shape (authoritative)

[REPO_STRUCTURE.md](REPO_STRUCTURE.md) defines six stages, now numerically
ordered:

```
00_specs/
|-- 01_ideas/
|-- 02_research/
|-- 03_requirements/
|-- 04_tasks/
|-- 05_prompts/
`-- 06_final/
```

The prior planning model in [00_planning/README.md](00_planning/README.md)
had 10 phases (intake → research → synthesis → feature → requirements →
stories → acceptance → tasks → tech-plan → prompt → dispatch). The current
6-folder shape is the simplified successor — we should not re-expand back to
10, but the planning doc is useful as a vocabulary reference (e.g. "acceptance
criteria belong inside requirements").

## Existing assets to reuse

- **Prompt library** — [12_prompts/](20_workspaces/12_prompts) already
  separates `roles/`, `tasks/`, `agents/`, `templates/`. The per-stage
  promotion prompts belong in `12_prompts/tasks/spec_promotion/` (one prompt
  per stage). They must stay provider-agnostic per
  [12_prompts/README.md](20_workspaces/12_prompts/README.md).
- **Model registry** — [13_models/registry.yaml](20_workspaces/13_models/registry.yaml)
  lists local Ollama models. LM Studio is declared as a provider in
  [13_models/providers.yaml](20_workspaces/13_models/providers.yaml) at
  `http://localhost:1234/v1` but has no models registered against it yet.
- **Notebook precedent** — [15_notebooks/local_ollama_tools_demo.ipynb](20_workspaces/15_notebooks/local_ollama_tools_demo.ipynb)
  is the only existing notebook and demonstrates the "shell out + observe"
  cell style we should mirror.
- **Path anchor** — `core.paths.WORKSPACES_ROOT` is the only sanctioned way to
  reach the spec tree; the notebook must not climb `__file__` parents.

## Layer ownership (classification audit constraints)

From [18_docs/classification_audit.md](20_workspaces/18_docs/classification_audit.md)
and [CLAUDE.md](CLAUDE.md):

- A workflow under [06_workflows/](20_workspaces/06_workflows) may orchestrate
  the promotion but must delegate **file I/O to drivers** and **LLM calls to
  harnesses** — it may not call providers directly.
- Adapters are stateless translators; the notebook is *not* an adapter.
- `02_core` stays domain-neutral — no spec-specific helpers go there.
- `11_mcp` is a thin exposure shim — when we later expose `/promote-spec` over
  MCP, that handler must not also fetch context, run the prompt, *and* write
  files in one tool.

The notebook itself sits in [15_notebooks/](20_workspaces/15_notebooks), which
is a sandbox layer and not audited the same way as the bucket layers. This is
exactly why the notebook is the right home for the *first* trigger — we can
prototype the orchestration shape before committing to a workflow placement.

## External dependencies

- An OpenAI-compatible chat endpoint. LM Studio (`localhost:1234/v1`) and
  Ollama (`localhost:11434/v1`) are both already declared as providers.
- Python `openai` client (already a common dep; not yet pinned in
  [20_workspaces/pyproject.toml](20_workspaces/pyproject.toml) — confirm in
  requirements stage).

## Open questions surfaced for the requirements stage

1. Does each stage prompt see *only* the previous stage's artifact, or the
   full chain of upstream artifacts? (Hypothesis: full chain, since the
   chain is short and the model needs the original idea's intent at every
   stage.)
2. What does `06_final/` contain? (Hypothesis: a single bundled prompt
   suitable for handing to a coding agent, plus an index linking to the
   per-stage artifacts.)
3. Is the notebook idempotent — re-running it overwrites stage files, or does
   it refuse to clobber? (Hypothesis: overwrite, with a confirmation cell.)
4. Should the notebook also write a `_meta.yaml` per stage capturing model,
   prompt version, and timestamp? (Hypothesis: yes, minimal — promotion has
   to be auditable for the audit-classification ethos to hold.)
