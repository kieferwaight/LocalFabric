# yaml-template-runtime-interpretter

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

- `stdlib.yaml` is always imported first (so any user yaml can `extends: abstract/base`).
- `--debug` prints the final scope as JSON to stdout.

### Example

```bash
python interpreter.py examples/deploy.yaml cloud/deployer \
    --service=billing --replicas=2 --canary=false --debug
```

## Project layout

```
interpreter.py          # CLI entry point
stdlib.yaml             # Built-in definitions (abstract/base, builtin/*)
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
tests/
  test_runtime.py       # BDD acceptance criteria
```

## Tests

```bash
python -m pytest tests
```
