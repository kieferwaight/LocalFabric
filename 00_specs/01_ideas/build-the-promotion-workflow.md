# Idea

## Summary

I want a [15_notebooks](15_notebooks) that promotes an idea
through the `00_specs/` pipeline — from `01_ideas/` to `06_final/` — by calling
a local LLM at each stage. The notebook is the observable "first trigger" for a
capability we will eventually expose as a `/promote-spec` command, an MCP tool,
and a pre-commit-hook-style automation.

## Trigger

The `00_specs/` folders are scaffolding with no automation. The first idea I
dropped in (`create-format-markdown-workflow.md`) made this visible — I have a
place to put ideas and a place to ship from, but nothing in the middle. I want
to build the connective tissue with the lightest possible mechanism (a
notebook) before committing to a heavier integration.

## Desired Outcome

Run a single notebook with `slug = "my-idea"` and observe each stage's
artifact appear in the matching `0N_<stage>/` folder. The promotion is
inspectable cell-by-cell so I can tune prompts and observe cause and effect
without rebuilding the whole pipeline.

## Unknowns

- Which prompts are needed per stage and how much context each one carries
  forward from earlier stages.
- Whether the same notebook can later be lifted into a workflow under
  [06_workflows/](06_workflows) without restructuring.
- How `06_final/` should differ from the union of upstream artifacts — is it a
  bundle, an index, or a frozen prompt for a coding agent?

## Strategy

Short-cut massive pipeline integration. Define the first trigger as a Python
notebook so the feature is conceptually visible before any cross-bucket
plumbing exists. Promote from idea to final by hand for *this* spec, then let
the notebook do it for the next one.
