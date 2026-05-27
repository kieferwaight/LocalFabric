# Requirements — add-example-runtime-to-tasks

Decisions made from the research stage. The runtime + CLI + a worked task
example are the deliverable; this file is the contract they satisfy.

Resolves the open questions raised in
[00_specs/02_research/add-example-runtime-to-tasks.md](00_specs/02_research/add-example-runtime-to-tasks.md).

## Functional requirements

### F1 — `examples:` is a top-level field on `Definition`

(Resolves research Q1.) Examples are metadata, not behavior. The
`Definition` dataclass in [02_core/runtimes/yaml/src/definition.py](02_core/runtimes/yaml/src/definition.py)
gains a new field `examples: list[Example]` parsed from the YAML's
top-level `examples:` block. No mixin or subclass is required; every
definition can declare examples for free.

Rejected alternatives: marker mixin `task.mixin.examples` (adds opt-in
friction for a feature that should be universal), `task.example.base`
subclass (forks the task hierarchy unnecessarily).

### F2 — `Example` schema

Each entry in `examples:` is a mapping:

```yaml
examples:
  - id: example.1                 # string, required, unique within the assembled set
    description: …                # string, optional, short prose
    inputs:                       # mapping, optional; keys must be declared inputs
      <input_name>: <value>
```

`id` must be a non-empty string and unique within the definition (and
within the assembled set after inheritance — see F6). `inputs` keys must
already exist in the definition's (post-assembly) `inputs:` declaration;
unknown keys fail at compile time. `inputs` values are subject to the
same `coerce_type()` and Jinja rendering as argument-supplied values.

`model`, `provider`, and any other override the user wants to reach via
an example are passed through as plain `inputs:` entries — there is no
new first-class top-level field on tasks for them (resolves research Q7).

### F3 — `--example=<id>` is a reserved CLI runtime flag

(Resolves research Q4.) A new runtime flag joins `--help`, `-h`, and
`--id` in the two-tier model documented at
[02_core/interfaces/cli/inventory.py:247-266](02_core/interfaces/cli/inventory.py#L247-L266).
Declared as a real `typer.Option`, so it is peeled out by Typer before
the `ctx.args` tail reaches `_parse_kv_args`.

Surfaces it must work on:

- `lfc run --example=example.1 ./path/to/task.yaml`
- `lfc task run image.classify.task --example=example.1`
- `lfc workflow run <workflow-id> --example=…`

`lfc prompt run` is intentionally excluded — prompts run through the
markdown harness, a different runtime path. Adding examples to prompts
is a separate spec.

No positional/subcommand form (`lfc task run … example.1`) — the named
flag is the single shape, to match `--id`.

### F4 — Override precedence

(Resolves research Q8.) When values are supplied from multiple places,
later layers override earlier ones in this order:

1. Input declaration `default:` (lowest)
2. Selected example's `inputs:` block
3. Explicit `--<name>=<value>` arguments (highest)

Implementation: the example's `inputs:` dict is merged into the
`arguments` dict *before* `_resolve_inputs()` runs
([runtime.py:585-602](02_core/runtimes/yaml/src/runtime.py#L585-L602)),
with explicit argument keys taking precedence.

### F5 — Unknown / missing example IDs fail loudly

`--example=does.not.exist` exits non-zero with a Rich-formatted error
that lists the available example IDs from the loaded definition, mirroring
how `_missing_args_help` ([inventory.py:231-244](02_core/interfaces/cli/inventory.py#L231-L244))
handles missing required inputs. Inside the runtime, `Runtime.execute()`
raises `ValueError` for unknown example IDs.

### F6 — Examples inherit through `extends:` and merge from `mixins:`

(Resolves research Q9.) `_assemble()` at
[02_core/runtimes/yaml/src/runtime.py:200-235](02_core/runtimes/yaml/src/runtime.py#L200-L235)
is extended to merge `examples:` lists with the same precedence as `inputs:`:
*base parent → mixins → local*, child wins on matching `id`. This lets a
domain-specific intermediate base ship a "smoke test" example that every
descendant inherits, while a child task can override or extend with its
own.

### F7 — `--help` output enumerates declared examples

`_print_run_help` ([inventory.py:206](02_core/interfaces/cli/inventory.py#L206))
gains an "Examples" Rich table when the loaded definition declares any.
Columns: `id`, `description`. Renders below the existing "inputs" table.
Empty examples list → table is omitted.

### F8 — Shell completion sources example IDs from the on-disk YAML

(Resolves research Q4.) The `--example` option declares an `autocompletion`
shim that reads the target YAML file directly (no runtime boot) and returns
its `examples[*].id` list. The inventory scanners
([inventory.py:124-151](02_core/interfaces/cli/inventory.py#L124-L151))
already demonstrate the live-from-disk pattern; completion reuses
`_parse_yaml_definition` for consistency.

### F9 — Examples are inline on the task YAML

(Resolves research Q5.) First cut: examples are authored inline as a
top-level `examples:` key on the task YAML. No sidecar
`<task>.examples.yaml` file format. Sidecars can be added later if churn
becomes a real problem; the engine API stays the same.

### F10 — Dataset references are opaque path strings

(Resolves research Q6.) When an example's `inputs:` value is a path like
`21_datasets/image/screenshot/lm-studio-model-explorer.001.dataset.yaml`,
the runtime treats it as a plain string. It is not auto-loaded, not
auto-validated, and not auto-resolved into structured fields. The task's
`lib.*` callable decides how to interpret the path. This preserves the
current boundary where datasets are reference metadata, not runtime
inputs.

### F11 — One worked example ships with the feature

[05_tasks/image.classify.task.yaml](05_tasks/image.classify.task.yaml)
gains a real `examples:` block referencing
[21_datasets/image/screenshot/lm-studio-model-explorer.001.dataset.yaml](21_datasets/image/screenshot/lm-studio-model-explorer.001.dataset.yaml).
This is both proof-of-life and the documentation pattern other task
authors copy.

## Non-functional requirements

### N1 — No backwards-compatibility shims

Per the project's no-back-compat stance, the new `examples:` field goes
straight onto `Definition`. No env-gated rollout, no `legacy_examples`
alias, no "old path still works." Tasks without examples continue to work
because the field defaults to an empty list.

### N2 — Pure-YAML mixin route is rejected, documented

The research stage established that a pure-mixin implementation is not
viable: `_resolve_inputs()` runs once at the start of `execute()`, so a
mixin's `run:` block has no chance to inject example values into inputs.
The implementation must live in core (`definition.py`, `compiler.py`,
`runtime.py`, `inventory.py`), not in a YAML mixin under
[02_core/runtimes/yaml/definitions/](02_core/runtimes/yaml/definitions/).

### N3 — Compile-time validation

The compiler ([02_core/runtimes/yaml/src/compiler.py](02_core/runtimes/yaml/src/compiler.py))
validates examples eagerly during assembly:

- `id` is non-empty and unique within the assembled set.
- Every key in `inputs:` is declared in the definition's (post-assembly)
  `inputs:` block.

Failures raise with the same `ValueError` shape used for unknown
`extends` / `mixins` references today
([compiler.py:46-54](02_core/runtimes/yaml/src/compiler.py#L46-L54)).

### N4 — Live-from-disk for CLI surfaces

`--help` rendering and `--example` completion both read the YAML
directly via the inventory scanner
([inventory.py:77-94](02_core/interfaces/cli/inventory.py#L77-L94)),
not via a runtime boot. This matches the existing inventory contract
that the file system is the source of truth between edits and runs.

### N5 — No new external dependencies

Implementation uses only what is already in `pyproject.toml`: Typer,
Jinja2, PyYAML, Rich.

## Acceptance criteria

A1. With the worked example from F11 in place,
    `lfc run --example=example.1 05_tasks/image.classify.task.yaml`
    executes the task with the dataset path bound to `path`, with no
    additional argument flags. Exit code is 0 when the underlying
    `classify_image` callable returns normally.

A2. `lfc run --example=example.1 --path=./other.png 05_tasks/image.classify.task.yaml`
    runs against `./other.png`, demonstrating explicit-flag override
    precedence (F4).

A3. `lfc run --example=missing 05_tasks/image.classify.task.yaml`
    exits non-zero and prints the available example IDs.

A4. `lfc run --help 05_tasks/image.classify.task.yaml` prints both the
    "inputs" table and the "Examples" table (F7).

A5. `lfc task run image.classify.task --example=example.1` works
    identically to the file-path form (F3).

A6. The new test module under [16_tests/](16_tests/) exercises:
    inheritance of examples through `extends:`, merge ordering from
    `mixins:`, override precedence (F4), and compile-time rejection of
    unknown input keys / duplicate IDs (N3).

A7. `uv run pytest` is green; `uv run ruff check` is clean.

## Out of scope

- **Per-example `hooks: before/after`** (resolves research Q3). The
  engine continues to expose only `teardown:` at the definition level.
  A symmetric `setup:` block and per-example hooks are deferred until a
  concrete use case forces the issue. Examples that need pre-execution
  setup can use Jinja conditionals against `entity_id` / a future
  `example_id` variable in the existing `run:` blocks.
- **Assertions / expected outputs / test-mode runner** (resolves
  research Q2). Examples in this cut are *fixtures*, not tests. A
  future `lfc test` verb or `examples[*].asserts:` field is a separate
  spec.
- **Sidecar `<task>.examples.yaml` files** (resolves research Q5 — F9).
- **Auto-resolution of dataset YAML paths into structured inputs**
  (resolves research Q6 — F10).
- **First-class `model:` / `provider:` top-level fields on YAML tasks**
  (resolves research Q7 — F2). Today they ride as plain inputs; promoting
  them is a separate concern that affects every task definition.
- **Renaming / repurposing the existing [15_examples/](15_examples/)
  bucket** (resolves research Q10). The idea note's distaste for that
  folder is acknowledged, but reorganising it is its own change and is
  not blocked by this feature. The vocabulary distinction in scope here:
  *task-attached examples* (this spec) vs *workflow example demos*
  (the existing `15_examples/*.example.yaml` files) — two different
  things that share a word.
- **Examples on markdown prompts** (`lfc prompt run --example=…`). The
  markdown harness is a separate runtime; adding examples to prompts is
  a separate spec.
- **Examples on `command.*` YAML-driven CLI verbs**
  ([02_core/interfaces/commands/](02_core/interfaces/commands/)). Only
  the `run`, `task run`, and `workflow run` surfaces get the
  `--example` flag in this cut.
