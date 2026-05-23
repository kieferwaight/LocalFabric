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
interpreter.py          # CLI entry point
stdlib/
  stdlib.yaml           # Primary built-in manifest (abstract/base and module loader)
  stdlib.files.yaml     # Filesystem write/create built-ins
  stdlib.git.yaml       # Git, GitHub CLI, and gitignore built-ins
  stdlib.template.yaml  # Template rendering built-ins
  stdlib.doc.yaml       # API-reference documentation built-ins
requirements.txt        # pyyaml, jinja2, pytest
runtime/
  shell_environment.py  # immutable env snapshot + CLI parser
  scope_frame.py        # lexically scoped variable frames
  definition.py         # Definition + InputConstraint dataclasses
  compiler.py           # YAML → registry, cycle detection
  jinja_engine.py       # multi-pass Jinja2 renderer
  dispatcher.py         # polyglot subprocess runner + state bridge
  runtime.py            # VM: import / assemble / execute
examples/
  deploy.yaml           # extends + mixins + multi-language run
  examples.yaml         # Example module manifest
  README.md             # Runnable composition index
  *.yaml                # Obsidian and Git example definitions
templates/docs/
  *.md.j2               # Authored Markdown layouts for generated API docs
docs/                   # Generated and committed YAML API reference
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
    - stdlib.template.yaml
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

The documentation reference is a YAML workflow built from `stdlib.template.yaml`
and `stdlib.doc.yaml`. From this directory, generate or verify committed pages:

```bash
python interpreter.py api-docs.yaml docs/api/reference --output_dir=docs --mode=write
python interpreter.py api-docs.yaml docs/api/reference --output_dir=docs --mode=check
```

The runtime exposes a read-only `runtime.catalog` during workflow execution.
`invoke` blocks can compose definitions and iterate catalog entries through
`for_each`, while native `template` blocks render authored Markdown assets.
The standard-library `artifact` operation delegates persistent writes and
directory creation to `drivers.file`.

## Tests

```bash
cd ../../..
python3 -m pytest 16_tests/workflows_yaml
```
