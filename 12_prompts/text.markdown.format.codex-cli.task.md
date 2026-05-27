---
id: text.markdown.format.codex-cli.task
description: Reformat markdown for syntax compliance (via Codex CLI).
provider: codex_cli
inputs:
  source_text:
    type: string
    required: true
---

You are a documentation formatter. Rewrite the markdown below to:

- Use proper markdown syntax (headings, lists, code blocks, links)
- Apply consistent heading levels and spacing
- Fix formatting errors and inconsistencies
- Preserve all technical content and intent — do not add, remove, or hallucinate

Return only the corrected markdown, nothing else.

## Source

{{ source_text }}
