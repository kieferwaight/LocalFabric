---
id: image.describe.copilot-cli.task
description: Describe what is visible in an image (via GitHub Copilot CLI).
provider: copilot_cli
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
