---
id: image.describe.lmstudio-gemma4.task
description: Describe what is visible in an image (via LM Studio, Gemma 4 E4B).
provider: lmstudio
model: google/gemma-4-e4b
max_tokens: 400
temperature: 0.0
inputs:
  image_path:
    type: string
    required: true
images:
  - "{{ image_path }}"
---

Describe what is visible in this image. Cover:

- Subjects, people, or objects in view
- Setting and environment
- Notable colors, mood, or style
- Any visible text (transcribed verbatim if short)

Keep the description factual and concise — 3 to 5 sentences. Do not speculate about context not visible in the image.
