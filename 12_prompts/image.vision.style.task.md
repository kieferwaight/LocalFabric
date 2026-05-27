---
id: image.vision.style.task
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
- End with <END>.
