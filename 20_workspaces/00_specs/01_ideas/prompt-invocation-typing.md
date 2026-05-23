# Idea

## Summary

The [`promote_spec.ipynb`](20_workspaces/15_notebooks/promote_spec.ipynb) flow
just surfaced a real coupling: a prompt, a model, an enabled-thinking flag, a
context budget, and a temperature only *work together* — but the code treats
`Prompt` as a string and passes the rest as loose kwargs to
`OpenAI.chat.completions.create()`. We got bitten when a reasoning model
spent its whole token budget thinking and returned empty `content`, and the
only place that knew the model needed ~18k context was a one-line note in
[`01_ideas/create-format-markdown-workflow.md`](20_workspaces/00_specs/01_ideas/create-format-markdown-workflow.md).

Introduce a small type system that names the coupling:

- **`Prompt` stays template-only** (text + declared variables, provider-agnostic
  — what [`12_prompts/README.md`](20_workspaces/12_prompts/README.md) already
  asks for).
- **`Model` gains capability fields** in [`13_models/registry.yaml`](20_workspaces/13_models/registry.yaml):
  `context_max`, `supports_thinking`, `default_temperature`, maybe
  `recommended_max_completion`.
- **`Provider` gains a `lifecycle` interface** (load/unload/health),
  implemented per-provider in [`04_harnesses/`](20_workspaces/04_harnesses).
  LM Studio has `lms load <model> --context-length N`; Ollama exposes
  equivalents via its REST API.
- **`Invocation`** is new — a `prompt × model × runtime-knobs` bundle that
  callers build instead of passing loose kwargs.

## Trigger

`promote_spec.ipynb` hit `finish_reason="length"` with empty `content`
because LM Studio's loaded context was 4096 while qwen3.6-27b supports ~18k.
The fix had to happen out-of-band — the user toggling LM Studio's UI to
reload the model with a higher context. If the registry entry for the model
knew its `context_max` and the provider supported
`lifecycle.ensure_loaded(model, context=…)`, the harness could have
guaranteed the right runtime without the user inspecting an error trace.

The bug is one symptom; the broader pattern is that *every* prompt in this
repo will eventually need a known-good `(model, context, temperature)`
binding, and we currently have no place to put that binding.

## Desired Outcome

For any prompt template, a caller (notebook, workflow, MCP tool) can say:

```python
invocation = Invocation(
    prompt=Prompt.load("tasks/spec_promotion/03_requirements.md"),
    model=registry["qwen3"],
    runtime=Runtime(temperature=0.2),
)
result = harness.invoke(invocation)
```

…and the harness picks the right provider, ensures the model is loaded with
sufficient context, runs the call, validates non-empty output, and returns a
typed result. Loose kwargs and silent empties go away.

## Unknowns

- Where do `Invocation` / `Runtime` / `Prompt` types live —
  [`01_contracts/`](20_workspaces/01_contracts) (just schemas) or
  [`02_core/`](20_workspaces/02_core) (runtime helpers too)? Probably both:
  schemas in contracts, builders/validators in core.
- Is `lms load` (LM Studio) + Ollama's REST `load` endpoint enough for a
  cross-provider `lifecycle.ensure_loaded()`, or do we need a fallback that
  prompts the user when automation isn't available (e.g., cloud providers)?
- Should `Invocation` carry the *expected* output schema too (so empty or
  malformed responses fail at the boundary rather than downstream), or is
  that a separate `Contract` type?
- What's the minimum useful slice? Hypothesis: capability fields on
  existing registry entries + an `Invocation` dataclass + one harness that
  respects it (LM Studio first). Everything else is follow-up.

## Strategy

Promote this idea through [`promote_spec.ipynb`](20_workspaces/15_notebooks/promote_spec.ipynb).
It is the second idea promoted through the pipeline (after
`build-the-promotion-workflow` itself) and the first one *not* hand-written —
making it the cleanest end-to-end test of the notebook against a fresh slug.
