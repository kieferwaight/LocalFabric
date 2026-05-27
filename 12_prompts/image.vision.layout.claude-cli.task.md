---
id: image.vision.layout.claude-cli.task
description: Describe only an image's page layout and spacing (via Claude CLI, Sonnet 4.6).
provider: claude_cli
model: claude-sonnet-4-6
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
