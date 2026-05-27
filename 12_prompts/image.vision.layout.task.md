---
id: image.vision.layout.task
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
- End with <END>.
