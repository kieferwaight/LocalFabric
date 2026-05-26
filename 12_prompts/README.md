# Prompt templates

Flat directory of prompt templates. Files use dot-notation in their names to
encode classification (no nested subdirectories). Every file declares an
`id:` in YAML frontmatter that matches the filename stem.

Naming convention follows the platform-wide pattern:

```
<domain>.<subdomain>.<action>.<type>.md
```

Where `<type>` is `task` for provider-agnostic task prompts or `example` for
runnable demo fixtures. Example: `image.vision.overview.task.md` has
`id: image.vision.overview.task`.

Current domains:

| Prefix | Purpose |
| --- | --- |
| `image.vision.*.task` | Vision sub-task prompts consumed by the image-intelligence workflow. |
| `spec.promotion.*.task` | Stage prompts for the spec promotion workflow (research → final). |
| `text.markdown.format.task` | Markdown formatter prompt consumed by `lib.text.format_markdown`. |
| `text.title.generate.task` | Title generation prompt. |
| `research.local.summarize.task` | Local research summarization prompt consumed by `lib.research.local_summarize`. |
| `<lang>.hello.example` | Hello-world demos for the markdown runtime harness. Also used as fixtures by `16_tests/harnesses.markdown.cli.test.py`. |
| `code.summarize.example` | Sample code-summarization prompt for the markdown runtime harness. |

The markdown runtime harness lives at `04_harnesses/markdown/`. See its
README for the file format, frontmatter schema, and CLI invocation.
