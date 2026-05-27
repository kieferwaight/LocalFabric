---
id: file.summarize.claude-cli.task
description: Summarize a file's content (via Claude CLI, Sonnet 4.6).
provider: claude_cli
model: claude-sonnet-4-6
inputs:
  source_text:
    type: string
    required: true
---

Summarize the content below. Include:

- The main topic and purpose
- Key points or arguments (use bullets if there are multiple)
- Any important caveats or conclusions

Keep the summary under 200 words. Preserve technical accuracy — do not invent facts.

## Content

{{ source_text }}
