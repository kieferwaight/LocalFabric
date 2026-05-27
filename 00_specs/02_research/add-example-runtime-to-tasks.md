# Research — add-example-runtime-to-tasks

Survey of what already exists in the repo that this spec must reuse or
respect. Findings only; decisions move to `03_requirements/`.

The idea note is [00_specs/01_ideas/ExpandedExampleRuntime.md](00_specs/01_ideas/ExpandedExampleRuntime.md) —
let task YAML files carry a named `examples:` block of input bundles so
`lfc run --example example.1 ./image.classify.task.yaml` can replay a
known-good invocation.

## Existing assets to reuse

- **Mixin system** — fully implemented and ready. [02_core/runtimes/yaml/src/definition.py:115](02_core/runtimes/yaml/src/definition.py#L115) declares `mixins: list[str]` on the `Definition` dataclass; [02_core/runtimes/yaml/src/compiler.py:52-68](02_core/runtimes/yaml/src/compiler.py#L52-L68) validates references and rejects cycles; [02_core/runtimes/yaml/src/runtime.py:200-235](02_core/runtimes/yaml/src/runtime.py#L200-L235) (`_assemble`) merges in order *base parent → mixins → local*, with the child winning. Existing precedent: [15_examples/](15_examples/) already holds `<area>.mixin.<purpose>.yaml` files (e.g. `cloud.mixin.git-info.yaml`).
- **Inheritance via `extends`** — `task.base` chains to `stdlib.base` ([02_core/runtimes/yaml/definitions/task.yaml](02_core/runtimes/yaml/definitions/task.yaml#L1-L12)). The assembler appends `run:` blocks, merges `inputs:` / `variables:` dicts.
- **Jinja2 multi-pass renderer** — [02_core/runtimes/yaml/src/jinja_engine.py](02_core/runtimes/yaml/src/jinja_engine.py) (`StrictUndefined`, up to 10 passes). `{{ path }}` substitution happens before the Python source is written to disk and executed as a subprocess.
- **`STATE_FILE` IPC** — set by [02_core/runtimes/yaml/src/dispatcher.py:68-73](02_core/runtimes/yaml/src/dispatcher.py#L68-L73) to a per-block temp JSON path; read back at lines 122-132 and merged into the scope at `runtime.py:660`. This is how task output is captured.
- **Teardown blocks** — `Definition.teardown` ([definition.py:120](02_core/runtimes/yaml/src/definition.py#L120)) is executed inside a `try/finally` around `run:` ([runtime.py:554-563](02_core/runtimes/yaml/src/runtime.py#L554-L563)). The "after" side of the proposal's `hooks:` is already there.
- **Input declaration + coercion** — `InputConstraint` ([definition.py:9-27](02_core/runtimes/yaml/src/definition.py#L9-L27)) with `type | required | default | description`; `_resolve_inputs` ([runtime.py:585-602](02_core/runtimes/yaml/src/runtime.py#L585-L602)) coerces argument values, falls back to defaults (which can themselves be Jinja-templated), raises on missing required.
- **Two-tier CLI flag model** — runtime flags vs task inputs are already a real distinction. Reserved flags are pulled out of `ctx.args` *before* the dynamic kv parser runs:
  - `--help`/`-h` is intercepted in both `_build_definition_group.run_cmd` ([02_core/interfaces/cli/inventory.py:376-378](02_core/interfaces/cli/inventory.py#L376-L378)) and the top-level file dispatcher ([inventory.py:532, 575, 597](02_core/interfaces/cli/inventory.py#L532)).
  - `--id` is a real `typer.Option` ([inventory.py:524](02_core/interfaces/cli/inventory.py#L524)).
  - `_parse_kv_args` ([inventory.py:247-266](02_core/interfaces/cli/inventory.py#L247-L266)) only sees what remains.
  - Contextual help is rendered by `_print_run_help` ([inventory.py:206](02_core/interfaces/cli/inventory.py#L206)) and already lists the loaded definition's inputs as a Rich table.

  Adding `--example` follows this established pattern.
- **CLI entry & live inventory** — `lfc` / `localfabric` Typer app at [02_core/interfaces/cli/main.py:90](02_core/interfaces/cli/main.py#L90); inventory groups (`task`, `workflow`, `prompt`, `service`) mounted by [02_core/interfaces/cli/inventory.py:624-657](02_core/interfaces/cli/inventory.py#L624-L657). Filesystem scanners (`scan_tasks`, etc.) parse YAML directly and stay in sync with edits — no reload step.
- **Datasets with reverse `uses:` links** — [21_datasets/image/screenshot/lm-studio-model-explorer.001.dataset.yaml](21_datasets/image/screenshot/lm-studio-model-explorer.001.dataset.yaml) already declares `uses: [task: image.vision.overview.task, asserts: ...]`. Examples-on-tasks are the *forward* counterpart and risk creating duplicate maintenance points.

## Layer-ownership constraints

- **`02_core/runtimes/yaml/`** owns the `Definition` dataclass, compilation, and execution. Anything that needs to inspect or merge `examples:` before `_resolve_inputs` runs lives here — not in a mixin's `run:` block (see "Critical engineering finding" below).
- **`02_core/interfaces/cli/`** owns runtime-flag wiring (`--help`, `--id`, future `--example`) and completion sources. Per the file's own docstring, inventory commands "read directly from the filesystem so it stays in sync with edits" — example-id completion must do the same, not require a runtime boot.
- **`15_examples/`** is currently a bucket for `*.example.yaml` workflow demos and `*.mixin.*.yaml` mixins. The word "example" is already overloaded with that bucket; introducing task-attached examples needs a clear vocabulary boundary in the requirements stage so the terminology stops colliding.
- **`05_tasks/`** holds the concrete `*.task.yaml` files where examples will be authored. No new bucket is needed for inline examples.
- **`21_datasets/`** owns dataset YAMLs and their `uses:` back-links. Examples may *reference* dataset paths but should not be the only place those links live — the dataset is authoritative for its own back-links.

## Critical engineering finding — pure-mixin implementation is not viable

The proposal's `task.example.mixin` route assumes a mixin's `run:` block can intercept inputs and merge example values into them. It cannot. `_resolve_inputs()` runs *once* at the start of `execute()`; by the time any `run:` block (base, mixin, or local) executes, inputs are already coerced and bound to the scope. There is no opportunity for a mixin to push `image_path: 21_datasets/…` into the scope under a key that is *also* a declared input.

Consequence: **examples must be a runtime-level concept** owned by the engine. A mixin can still appear as a *marker / schema contract* (analogous to how `extends` is YAML-declared but resolved by the compiler), but the merge step is core code, not YAML composition.

## Naming taxonomy

Existing patterns in the repo:

- **Base IDs:** `<area>.base` — `task.base`, `workflow.base`, `model.base`, `stdlib.base`, `docker.base`, `command.base`, `folder.base`, `route.base`, `service.base`, `provider.base`. The check in [runtime.py:278-285](02_core/runtimes/yaml/src/runtime.py#L278-L285) treats these as a closed-enum taxonomy (`has_task`, `has_workflow`, etc.).
- **Mixin files:** `<area>.mixin.<purpose>.yaml` — `cloud.mixin.git-info.yaml`, `cloud.mixin.timestamp.yaml`. The `mixin` token sits in the middle, not the tail.

The idea note's `task.example.mixin` matches neither shape. Conformant alternatives, decisions deferred:

- Mixin-style: `task.mixin.examples` (plural — examples is a collection).
- Base-subclass-style: `task.example.base` (the note's other suggestion — forks the hierarchy).
- Or no taxonomy entry at all, if `examples:` becomes a top-level field on every `Definition` (most consistent with `inputs:`, `variables:`, `tags:`).

Also: the note's mixin sketch types `inputs.example` as `integer`, but the example IDs in the same file are strings (`example.1`). The CLI/runtime contract is string-keyed.

## What does not exist yet (will need to be added)

- **No `examples:` field on `Definition`.** Adding it means extending [definition.py:108-167](02_core/runtimes/yaml/src/definition.py#L108-L167) (dataclass + `from_dict`) and `_assemble()` in runtime so examples inherit through `extends`/`mixins`.
- **No `setup:` / `before:` block** — only `teardown:`. Per-example pre-execution hooks would need at minimum a symmetric setup primitive.
- **No reserved `--example` runtime flag yet** — but the pattern (`--help`, `-h`, `--id`) is established, so this is a clean addition.
- **No example-id resolver** — picking `example.1` out of a definition's `examples:` list and merging its `inputs:` into the arguments dict before `_resolve_inputs()` is new code.
- **No first-class `model:` / `provider:` top-level fields on YAML tasks.** Today `model`/`provider` are plain string inputs in tasks like `embeddings.embed.text.task.yaml`; markdown harnesses have first-class provider markers but YAML tasks do not. The proposal's `model: claude-haiku-4-5` example override works *if treated as a plain input override*; promoting them to top-level fields is a separate concern.
- **No preset / profile / override-from-file precedent.** Examples will be the first such mechanism — no prior art in-repo to mirror.
- **No assertion / test-runner machinery for tasks.** The note hints that examples are "sometimes similar to tests" but the runtime has no notion of expected outputs or pass/fail.

## External dependencies

None new. The feature builds on Typer, Jinja2, and PyYAML — all already pinned.

## Open questions for requirements stage

1. **Shape of the declaration** — top-level field on every `Definition` (option A), marker mixin `task.mixin.examples` + runtime support (option B), or new base `task.example.base` (option C)? See "Naming taxonomy" above for the three shapes.
2. **Examples as tests, fixtures, or both?** The note says "sometimes similar to tests" but does not commit. Does the first cut include assertions / expected outputs, or just input bundles?
3. **Hooks shape** — per-example `hooks: before/after` blocks (as drawn in the note), or a symmetric definition-level `setup:` mirroring the existing `teardown:`? The latter is engine-simpler and decouples hooks from examples.
4. **CLI surface for `--example`** — declare it as a single reserved runtime flag on `lfc run` / `lfc task run` (following the `--help` / `--id` precedent), or also expose example IDs as a positional/subcommand (`lfc task run image.classify.task example.1`)? What is the completion source — load the YAML and enumerate `examples[*].id`? Show example descriptions in `--help` output the same way inputs are listed today via `_print_run_help`?
5. **Inline vs. sidecar** — examples authored inline on each task YAML, or in a sibling `<task>.examples.yaml`? Sidecars decouple churn (changing examples does not rev the task file) but add discovery cost.
6. **Dataset reference semantics** — does the runtime *resolve* a `21_datasets/...dataset.yaml` path into structured inputs, or pass the path string through and let the task's `lib.*` callable decide? Today datasets are not consumed by the runtime; treating example paths as opaque strings preserves that boundary.
7. **`model:` / `provider:` overrides** — keep as plain input overrides (zero engine changes needed), or promote to first-class top-level fields on tasks? The latter affects every task definition, not just ones with examples.
8. **Override precedence** — when both `--example=X` and explicit `--input=Y` are passed, which wins? Plausible default: explicit CLI flags override example values, which override declared defaults.
9. **Inheritance semantics** — do examples inherit through `extends:` and merge from `mixins:` the same way `inputs:` does (child appends, child wins on same id)? Or are examples local-only?
10. **Relationship to `15_examples/`** — the word "example" is already overloaded with the existing bucket of `*.example.yaml` workflow demos. Do task-attached examples need a different noun, or does the bucket get renamed/repurposed?
