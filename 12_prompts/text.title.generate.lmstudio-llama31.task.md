---
id: text.title.generate.lmstudio-llama31.task
description: Generate a concise title for text (via LM Studio, Llama 3.1 8B).
provider: lmstudio
model: meta-llama-3.1-8b-instruct
max_tokens: 60
temperature: 0.3
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
