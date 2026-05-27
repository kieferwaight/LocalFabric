---
id: image.vision.layout.lmstudio-gemma4.task
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

Describe only the page structure and spacing.
Return exactly this markdown shape:

## Layout

- Header: <short description>
- Main area: <short description>
- Lower area: <short description>
- Footer: <short description>

Rules:

- Maximum 4 bullets.
- Do not transcribe any visible text.
- Do not list navigation items, headings, or button labels one by one.
- Mention only large visible blocks, media, CTA areas, and spacing.
- No placeholders except the angle-bracket examples in this template.
