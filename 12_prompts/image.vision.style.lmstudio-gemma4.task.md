---
id: image.vision.style.lmstudio-gemma4.task
description: Describe an image's visual style (via LM Studio, Gemma 4 E4B).
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

Describe only the visible visual style.
Return exactly this markdown shape:

## Style

- Color: <short description>
- Typography: <short description>
- Imagery: <short description>
- Composition: <short description>

Rules:

- Maximum 4 bullets.
- Visible facts only.
- Do not transcribe text.
- Do not invent brand meaning or strategy.
- No placeholders except the angle-bracket examples in this template.
