---
id: image.vision.visible-text.task
provider: ollama
model: llama3.2-vision
max_tokens: 220
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

Extract only the exact visible text from the image.
Return exactly this markdown shape:

## Text

- \<exact visible text line 1>
- \<exact visible text line 2>
- \<exact visible text line 3>
  Rules:
- Maximum 8 bullets.
- Preserve exact wording and line breaks as much as possible.
- Do not summarize.
- Do not explain the text.
- Do not repeat any extracted line.
- If nothing is readable, return one bullet: "No readable text."
- No placeholders except the angle-bracket examples in this template.
- End with <END>.
