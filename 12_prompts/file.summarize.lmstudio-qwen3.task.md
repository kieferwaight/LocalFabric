---
id: file.summarize.lmstudio-qwen3.task
description: Summarize a file's content (via LM Studio, Qwen3 27B).
provider: lmstudio
model: qwen/qwen3.6-27b
max_tokens: 600
temperature: 0.2
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
