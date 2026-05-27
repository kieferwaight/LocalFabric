---
id: image.describe.ollama.task
description: Describe what is visible in an image (via Ollama, Llama 3.2 Vision).
provider: ollama
model: llama3.2-vision
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
