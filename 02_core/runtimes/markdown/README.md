# Markdown Runtime Harness

A thin compile-and-dispatch shim that turns `.md` files into either YAML
workflow definitions *or* provider prompts:

- **Fence-style** files (no `provider:` in frontmatter) compile into a YAML
  runtime definition whose `run:` list is built from fenced bash/python/js
  code blocks. The YAML runtime owns execution, inheritance, scope, and the
  IPC state bridge — the harness owns markdown ingest only.
- **Provider-style** files (`provider:` declared in frontmatter) skip the
  YAML runtime entirely. The body is treated as a single Jinja-renderable
  prompt and dispatched through `harnesses.markdown.providers` to the
  matching provider harness (e.g. `harnesses.claude.ClaudeHarness`).

## File format

Every `.md` file processed by the harness begins with a YAML frontmatter
block (delimited by `---`) and is followed by a body of arbitrary markdown.

````markdown
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
````

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

# Fence-style files return the final scope dict.
final_scope = harness.execute(path, arguments={"name": "world"})

# Provider-style files return a ProviderResult — or an iterator of text
# chunks when the file requests streaming.
result = harness.execute("examples.summarize-code.md", arguments={"input": "def f(): ..."})
print(result.text)
```

`MarkdownCompileError` is raised for malformed markdown (missing
frontmatter, missing/invalid `id`, duplicate block ids, malformed fence
attributes). Runtime errors propagate unchanged from `workflows.yaml`.

## CLI

```
python -m adapters.cli.markdown_runtime_adapter <markdown_file> [--key=value] [--flag]
```

The adapter parses argv via the YAML runtime's `ShellEnvironment.from_argv`,
auto-imports the YAML stdlib, instantiates `MarkdownHarness`, and runs the
file. Pass `--debug` to dump the final scope as JSON.

Example:

```
python -m adapters.cli.markdown_runtime_adapter 12_prompts/examples.hello-polyglot.md \
    --name=World --debug
```

## Provider-style files

When frontmatter declares `provider:`, the file describes a single prompt
sent to a hosted LLM rather than a workflow of fence blocks. The body is
the prompt template; Jinja tokens resolve against declared `inputs` and
any CLI arguments.

```markdown
---
id: examples.summarize-code
description: Summarize a code file using Claude
provider: claude
model: claude-sonnet-4-6
inputs:
  input:
    type: string
    required: true
---

You are a senior engineer. Summarize the following code clearly and concisely:

{{ input }}
```

Supported frontmatter fields:

| Field | Type | Purpose |
| --- | --- | --- |
| `provider` | string (required) | Provider key registered in `harnesses.markdown.providers.PROVIDERS`. |
| `model` | string | Model id passed to the provider; per-provider default applies when omitted. |
| `system` | string | Optional system prompt forwarded to the provider. |
| `max_tokens` | integer | Upper bound on response tokens. |
| `temperature` | number | Sampling temperature. |
| `stream` | boolean | When `true`, the harness streams chunks to stdout and returns an iterator instead of a `ProviderResult`. |
| `inputs` | mapping | Same shape as fence-style inputs; values are rendered into the prompt body. |

Provider-style files do **not** support fence-style keys (`extends`,
`mixins`, `modules`, `variables`) — the compiler rejects them with a clear
error rather than silently no-op.

### Built-in providers

| Name | Backed by | Default model | Auth |
| --- | --- | --- | --- |
| `claude` | `harnesses.claude.ClaudeHarness` | `claude-sonnet-4-6` | `ANTHROPIC_API_KEY` env var |

`ClaudeProvider` lazily constructs its underlying harness — importing it
doesn't require the `anthropic` SDK. The first call to `.run()` triggers
the SDK import and key check; missing `ANTHROPIC_API_KEY` surfaces as a
`ProviderError` with a clear message.

To register a custom provider:

```python
from harnesses.markdown.providers import register_provider

register_provider("my-provider", MyProviderFactory)
```

Tests can inject a stub provider without touching the global registry:

```python
harness = MarkdownHarness(provider_overrides={"claude": stub_provider})
```

## Out of scope

- Inter-block I/O (`BLOCK_<id>_STDOUT` env vars) for fence-style files.
  See the YAML dispatcher.
- LLM blocks via `claude` / `ollama` fence languages — the provider-style
  file shape covers the LLM dispatch use case.
