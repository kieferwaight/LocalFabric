---
id: image.vision.overview.lmstudio-gemma4.task
provider: lmstudio
model: google/gemma-4-e4b
max_tokens: 1200
temperature: 0.0
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
