# YAML Polyglot Runtime

A YAML-driven polyglot abstract state machine. Definitions are written in YAML,
support inheritance (`extends`) and mixin composition, and execute polyglot
`run` blocks (`bash` / `python` / `node`) through a multi-pass Jinja2 templating
layer with an IPC state bridge that flows values back into the active scope
frame.

## Install

Install the LocalFabric workspace once from the repo root — that registers the
`workflows` import alias and the dev/test toolchain:

```bash
cd ../..              # repo root
pip install -e ".[dev]"
```

No requirements file lives in this bucket; runtime dependencies (`PyYAML`,
`Jinja2`) are declared in the root [pyproject.toml](../../pyproject.toml).

## Usage

```bash
python interpreter.py <yaml_file> <definition_id> [positional args] [--key=value] [--flag]
```

- [definitions/stdlib.yaml](definitions/stdlib.yaml) is auto-imported before any
  user file. It defines the `stdlib.base` abstract frame and
  `stdlib.load-modules.workflow`, which pulls in the namespaced standard library modules.
- The `<yaml_file>` argument is the file containing (or transitively importing)
  `<definition_id>`. Pass a path relative to this directory.
- `--debug` prints the final scope frame as JSON to stdout.

### Example

```bash
python interpreter.py ../../../../15_examples/cloud.yaml cloud.deployer.example \
    --service=billing --replicas=2 --canary=false --debug
```

## Project layout

```
interpreter.py            # CLI entry point
src/                      # Runtime VM (importable as workflows.yaml.src)
  shell_environment.py    # immutable env snapshot + CLI parser
  scope_frame.py          # lexically scoped variable frames
  definition.py           # Definition + TemplateBlock + InputConstraint dataclasses
  compiler.py             # YAML → registry, cycle detection
  jinja_engine.py         # multi-pass Jinja2 renderer (+ resolve_argument)
  dispatcher.py           # polyglot subprocess runner + state bridge
  file_io.py              # artifact / directory operations
  runtime.py              # VM: import / assemble / execute / render
  yaml_analysis.py        # static catalog inspection
definitions/              # Flat YAML library (one or more definitions per file)
  stdlib.yaml             # abstract base + module loader (auto-imported)
  stdlib.files.yaml       # filesystem write/create
  stdlib.git.yaml         # git, gh CLI, gitignore
  stdlib.docs.yaml        # prune-definition-pages helper
  docs.yaml               # docs.api.reference workflow (entry point)
  docs.catalog.yaml       # source catalog for the generated reference
  docs.definition.template.yaml   # Jinja templates for each generated page
  examples.catalog.yaml   # catalog of runnable example definitions
docs/                     # Generated YAML API reference (committed)
```

## Standard Library Modules

A definition can declare relative YAML dependencies with `modules:`.
`stdlib.load-modules.workflow` uses this to keep a single default import while built-ins
stay grouped by namespace:

```yaml
- id: stdlib.load-modules.workflow
  modules:
    - stdlib.files.yaml
    - stdlib.git.yaml
    - stdlib.docs.yaml
```

`stdlib.files.write-text.task` expands `[[OPEN_TEMPLATE]]` and `[[CLOSE_TEMPLATE]]`
while writing, so examples can safely emit literal Obsidian template tokens
through the multi-pass Jinja renderer.

## API Documentation

Definitions can describe their public contract without affecting runtime
behavior:

```yaml
- id: stdlib.files.write-text.task
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
Input descriptions are defined by `inputs.<name>.description`.

The documentation workflow `docs.api.reference` lives in
[definitions/docs.yaml](definitions/docs.yaml) and composes the reusable
template definitions in
[definitions/docs.definition.template.yaml](definitions/docs.definition.template.yaml).
From this directory, generate or verify committed pages:

```bash
python interpreter.py definitions/docs.yaml docs.api.reference --output_dir=docs --mode=write
python interpreter.py definitions/docs.yaml docs.api.reference --output_dir=docs --mode=check
```

The runtime exposes a read-only `runtime.catalog` during workflow execution.
`invoke` blocks compose definitions and iterate catalog entries through
`for_each`. `render` blocks invoke a template definition (any definition with a
top-level `template:` block) and write the rendered string to `target_path`.
Inside a template body, the `component('definition-id', **kwargs)` Jinja helper
renders another template definition inline. The `artifact` operation delegates
persistent writes and directory creation to `drivers.file`.

## Tests

From the repo root:

```bash
pytest 16_tests/workflows_yaml
```
