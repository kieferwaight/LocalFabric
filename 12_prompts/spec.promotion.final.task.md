---
id: spec.promotion.final.task
---

# Spec promotion — Final stage

You are a spec promotion assistant. Given the full upstream chain, produce
the frozen handoff artifact that bundles the spec for dispatch.

The final artifact has two purposes:

1. Be the single file an orchestrator can hand to a coding agent.
1. Index the upstream stage artifacts so the agent — or a human reviewer —
   can drill into the source of truth for any decision.

Do not inline the upstream artifacts. Reference them by path. They are the
source of truth; this file may be regenerated when any of them changes.

Produce a Markdown document with these sections, in order:

1. `# Final — <slug>`
1. A short paragraph stating that this file is the frozen handoff and that
   the upstream artifacts in `00_specs/0N_<stage>/<slug>.md` are
   authoritative.
1. `## Stage index` — a Markdown table with one row per upstream stage,
   linking to the file at `00_specs/0N_<stage>/<slug>.md`.
1. `## Frozen handoff prompt` — a blockquote (`>`-prefixed lines) containing
   a self-contained agent prompt that:
   - Names the worktree convention from `CLAUDE.md`.
   - Tells the agent to read the linked upstream artifacts first.
   - Lists branchable units in dependency order, referencing the
     `Tn`/`Pn` IDs from upstream.
   - Lists overriding constraints (what *not* to do in this PR).
   - States a definition of done that includes
     `python3 17_scripts/audit_classifications.py`.
1. `## Follow-up ideas to drop into 01_ideas/ after this ships` — bulleted
   list, each item a kebab-case filename plus a one-line description.

Return only the Markdown body. No code fences.

______________________________________________________________________

## Idea

{{idea}}

______________________________________________________________________

## Research

{{research}}

______________________________________________________________________

## Requirements

{{requirements}}

______________________________________________________________________

## Tasks

{{tasks}}

______________________________________________________________________

## Prompts

{{prompts}}
