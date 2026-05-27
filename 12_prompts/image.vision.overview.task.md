---
id: image.vision.overview.task
provider: ollama
model: llama3.2-vision
max_tokens: 180
temperature: 0.0
stop:
  - <END>
  - "\n## END"
options:
  top_p: 0.8
  top_k: 20
  repeat_penalty: 1.35
  repeat_last_n: 256
inputs:
  image_path:
    type: string
    required: true
images:
  - "{{ image_path }}"
---

Describe only the overall visible content.
Return exactly this markdown shape:

## Overview

- Subject: <short description>
- Context: <short description>
- Visible elements: <short description>
- Notes: <short description>
  Rules:
- Maximum 4 bullets.
- Visible facts only.
- Do not transcribe text.
- Do not invent content that is not clearly visible.
- No placeholders except the angle-bracket examples in this template.
- End with <END>.
