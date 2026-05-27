---
id: text.title.generate.ollama.task
description: Generate a concise title for text (via Ollama, Qwen 2.5 7B).
provider: ollama
model: qwen2.5:7b
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
