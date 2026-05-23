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
notebooks/
  README.md             # Runnable routine index
  *.yaml                # Obsidian and Git routine definitions
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
```

`builtin/files/write-text` expands `[[OPEN_TEMPLATE]]` and
`[[CLOSE_TEMPLATE]]` while writing, so YAML notebooks can safely emit literal
Obsidian template tokens through the multi-pass Jinja renderer.

## Tests

```bash
cd ../../..
python3 -m pytest 16_tests/workflows_yaml
```
