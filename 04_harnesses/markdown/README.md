# Markdown Runtime Harness

A thin compile-and-dispatch shim that turns `.md` files into definitions the
YAML workflow runtime executes. The harness owns markdown ingest only —
script execution, inheritance, scope frames, and the IPC state bridge stay
with `workflows.yaml`.

## File format

Every `.md` file processed by the harness begins with a YAML frontmatter
block (delimited by `---`) and is followed by a body of arbitrary markdown.

```markdown
---
id: examples.hello
title: Hello example
inputs:
  name:
    type: string
    required: true
---

# Hello

```bash {id: greet}
echo "Hello, {{ name }}!"
```
```

Frontmatter fields mirror the YAML definition schema: `id` (required),
`title`, `description`, `tags`, `extends`, `mixins`, `modules`, `inputs`,
`variables`. The full body text — including the fences themselves — is
bound to a `body` variable on the assembled definition unless the author
explicitly declares a `body:` under `variables:`.

### Recognized fence languages

| Markdown fence | Dispatcher language |
| --- | --- |
| ` ```bash ` / ` ```sh ` | `bash` / `sh` |
| ` ```python ` / ` ```py ` | `python` |
| ` ```js ` / ` ```javascript ` / ` ```node ` | `js` |

Other language tokens — `ollama`, `claude`, `mermaid`, plain text, etc. — and
fences with no language token are recognized but not run; they survive as
documentation. A warning is logged when an unrecognized language is
encountered.

### Fence attributes

Attributes after the language token use YAML flow-mapping syntax:

````
```python {id: greet, description: "say hi", skip: false}
print("hi")
```
````

Recognized attributes in step 1:

- `id` (string) — block identifier; must be unique within a file.
- `description` (string) — human-readable purpose; preserved as metadata.
- `skip` (boolean) — when `true`, the block is omitted from the compiled
  `run` list. Block ids on skipped blocks still count toward uniqueness.
- `working_dir` (string) — preserved as metadata for steps 2 and 3.

Unrecognized attributes are preserved as `_markdown_attributes` on the
compiled block — forward-compatibility for inter-block I/O and LLM blocks
that land in later steps.

## Documented limitations

- **Nested fences are not supported.** The first line matching `^\s*```\s*$`
  after the opening fence terminates the block. Authors who want to show a
  fence inside documentation should use indentation rather than nesting.
- **Unknown languages do not execute.** They are preserved as documentation
  only; a warning is emitted at compile time.
- **`title` falls back to the body's first H1.** If the frontmatter omits
  `title`, the compiler scans the body for a leading `# heading` and uses
  that. Failing both, the definition `id` becomes the title at runtime.

## Public API

```python
from harnesses.markdown import MarkdownHarness, MarkdownCompileError

harness = MarkdownHarness()              # spins up a default Runtime
harness.compile_text(source, source_path=...)  # pure: text → definition dict
harness.compile_file(path)               # read + compile
harness.register(path)                   # compile + import into runtime
harness.register_dir(path, recursive=True)
final_scope = harness.execute(path, arguments={"name": "world"})
```

`MarkdownCompileError` is raised for malformed markdown (missing
frontmatter, missing/invalid `id`, duplicate block ids, malformed fence
attributes). Runtime errors propagate unchanged from `workflows.yaml`.

## CLI

```
python -m adapters.cli.markdown <markdown_file> [--key=value] [--flag]
```

The adapter parses argv via the YAML runtime's `ShellEnvironment.from_argv`,
auto-imports the YAML stdlib, instantiates `MarkdownHarness`, and runs the
file. Pass `--debug` to dump the final scope as JSON.

Example:

```
python -m adapters.cli.markdown 12_prompts/markdown/examples/hello-polyglot.md \
    --name=World --debug
```

## Out of scope (steps 2 and 3)

- Inter-block I/O (`BLOCK_<id>_STDOUT` env vars). See the YAML dispatcher.
- LLM operations — `ollama` / `claude` fences compiled to a `model:`
  structured op.

The forward-compat attribute pass-through (`_markdown_attributes`) is the
seam these later steps will hook into.
