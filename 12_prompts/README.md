# Prompt templates

Flat directory of prompt templates. Files use dot-notation in their names to
encode classification (no nested subdirectories). Every file declares an
`id:` in YAML frontmatter that matches the filename stem.

Naming convention:

```
<namespace>[.<sub-namespace>...].<slug>.md
```

Example: `tasks.vision.overview.md` has `id: tasks.vision.overview`.

Current namespaces:

| Prefix | Purpose |
| --- | --- |
| `tasks.*` | Provider-agnostic task prompts loaded by workflows and tools. |
| `tasks.vision.*` | Vision sub-task prompts consumed by the image-intelligence workflow. |
| `tasks.spec-promotion.*` | Stage prompts for the spec promotion workflow (research → final). |
| `examples.*` | Runnable demos for the markdown runtime harness. Also used as fixtures by `16_tests/harnesses.markdown.cli.test.py`. |

The markdown runtime harness lives at `04_harnesses/markdown/`. See its
README for the file format, frontmatter schema, and CLI invocation.
