# Task prompts

Flat directory of provider-agnostic task prompts consumed at runtime by
LangGraph nodes and `lib.*` helpers. Files use dot-notation in their names
to encode classification (no nested subdirectories). Every file declares
an `id:` in YAML frontmatter that matches the filename stem.

Naming convention follows the platform-wide pattern:

```
<domain>.<subdomain>.<action>.task.md
```

Example: `image.vision.overview.task.md` has `id: image.vision.overview.task`.

Current domains:

| Prefix                          | Purpose                                                                         |
| ------------------------------- | ------------------------------------------------------------------------------- |
| `image.vision.*.task`           | Vision sub-task prompts consumed by the image-intelligence workflow.            |
| `spec.promotion.*.task`         | Stage prompts for the spec promotion workflow (research → final).               |
| `text.markdown.format.task`     | Markdown formatter prompt consumed by `lib.text.format_markdown`.               |
| `text.title.generate.task`      | Title generation prompt.                                                        |
| `research.local.summarize.task` | Local research summarization prompt consumed by `lib.research.local_summarize`. |

Runnable demos and example prompts live in `15_examples/` instead.

The markdown runtime harness lives at `04_harnesses/markdown/`. See its
README for the file format, frontmatter schema, and CLI invocation.
