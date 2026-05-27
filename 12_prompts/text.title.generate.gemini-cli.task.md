---
id: text.title.generate.gemini-cli.task
description: Generate a concise title for text (via Gemini CLI).
provider: gemini_cli
inputs:
  source_text:
    type: string
    required: true
---

Generate the single best title for the text below.

Requirements:

- 5 to 10 words
- Specific and descriptive
- Executive tone
- No filler words
- Return only the title — no quotes, no trailing punctuation, no commentary

## Text

{{ source_text }}
