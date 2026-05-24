# yaml-template-runtime-interpreter

A YAML-driven polyglot abstract state machine runtime interpreter.

Definitions are expressed in YAML, support inheritance (`extends`) and mixins,
and execute polyglot `run` blocks (bash / python / node) with a Jinja2 templating
layer and an IPC state bridge that flows values back into the active scope frame.

## Install

```bash
pip install -r requirements.txt
```

## Usage

```bash
python interpreter.py <yaml_file> <definition_id> [positional args] [--key=value] [--flag]
```

- `stdlib/stdlib.yaml` is always imported first, and its `builtin/load-modules`
  definition loads namespaced built-ins such as `stdlib.git.yaml`.
- `--debug` prints the final scope as JSON to stdout.

### Example

```bash
python interpreter.py examples/deploy.yaml cloud/deployer \
    --service=billing --replicas=2 --canary=false --debug
```

## Project layout

```
interpreter.py          # CLI entry point (reusable)
config.yaml             # Project-unique manifest: docs workflow + example catalog
stdlib/                 # Reusable built-ins, auto-loaded
  stdlib.yaml           # abstract/base + module loader
  stdlib.files.yaml     # filesystem write/create
  stdlib.git.yaml       # git, gh CLI, gitignore
  stdlib.doc.yaml       # prune-definition-pages helper
runtime/                # Reusable VM
  shell_environment.py  # immutable env snapshot + CLI parser
  scope_frame.py        # lexically scoped variable frames
  definition.py         # Definition + TemplateBlock + InputConstraint dataclasses
  compiler.py           # YAML → registry, cycle detection
  jinja_engine.py       # multi-pass Jinja2 renderer (+ resolve_argument)
  dispatcher.py         # polyglot subprocess runner + state bridge
  runtime.py            # VM: import / assemble / execute / render
templates/              # Reusable doc templates (flat YAML, one definition per file)
  doc-index.yaml        # README page
  doc-schema.yaml       # Authoring schema page
  doc-definition.yaml   # Per-definition page
  doc-component-*.yaml  # Reusable template components (e.g. relationship graph)
examples/               # Project-unique runnable example definitions
docs/                   # Generated YAML API reference (flat sibling-linked files)
```

## Standard Library Modules

A definition can declare relative YAML dependencies with `modules:`. The
primary standard library uses this on `builtin/load-modules`, keeping one
default import while built-ins remain grouped by namespace:

```yaml
- id: builtin/load-modules
  modules:
    - stdlib.files.yaml
    - stdlib.git.yaml
    - stdlib.doc.yaml
```

`builtin/files/write-text` expands `[[OPEN_TEMPLATE]]` and
`[[CLOSE_TEMPLATE]]` while writing, so YAML examples can safely emit literal
Obsidian template tokens through the multi-pass Jinja renderer. Runnable
compositions belong in `examples/`, while `stdlib/` is reserved for
auto-loaded reusable primitives.

## API Documentation

Definitions can describe their public contract without affecting runtime behavior:

```yaml
- id: builtin/files/write-text
  title: Write Text File
  description: |
    Writes rendered UTF-8 content to a target path.
  tags: [files, templates]
  docs:
    variables:
      content: Text content to write.
    run:
      - title: Write rendered content
```

`title`, Markdown `description`, `tags`, and `docs` enrich generated pages.
Input descriptions continue to be defined by `inputs.<name>.description`.

The documentation workflow lives in `config.yaml` and composes the reusable
template definitions under `templates/`. From this directory, generate or verify
committed pages:

```bash
python interpreter.py config.yaml docs/api/reference --output_dir=docs --mode=write
python interpreter.py config.yaml docs/api/reference --output_dir=docs --mode=check
```

The runtime exposes a read-only `runtime.catalog` during workflow execution.
`invoke` blocks compose definitions and iterate catalog entries through
`for_each`. `render` blocks invoke a template definition (any definition with
a top-level `template:` block) and write the rendered string to `target_path`.
Inside a template body, the `component('definition-id', **kwargs)` Jinja helper
renders another template definition inline. The `artifact` operation delegates
persistent writes and directory creation to `drivers.file`.

## Tests

```bash
cd ../../..
python3 -m pytest 16_tests/workflows_yaml
```
