# Create a CLI harness

This was an attempt that didnt go quite as hoped, however it did have some storng points.
15_examples/code.summarize.example.md

1) It displays loading and user feedback.

What we need is a harness system that operates with the same interface and functionality as other models
For example `12_prompts/image.vision.layout.task.md` uses llama3.2-vision.  We should have a harness that
supports passing an image to codex, gemini, copilot, and claude.


Gemini has already been tested

```
gemini --skip-trust -p "Describe this image ./img"
```

It does parse the path on its own, but thats not an issue. It does take input and can handle the image feature
as a model just likellama3.2-vision.  We need to crate unified interfaces so that I can write this same exact 
prompt

# Claude
```
---
id: image.vision.layout.task
provider: claude
model: claude-opus-4-7
inputs:
  image_path:
    type: string
    required: true
images:
  - "{{ image_path }}"
---

Describe only the page structure and spacing.
Return exactly this markdown shape:

.... etc
```

# Gemini
```
---
id: image.vision.layout.task
provider: gemini
model: gemma3
inputs:
  image_path:
    type: string
    required: true
images:
  - "{{ image_path }}"
---

Describe only the page structure and spacing.
Return exactly this markdown shape:

.... etc
```

We can handle both text, image, and a few other possibilities. The harness/ or driver/ or whatever it should be called needs to be independant of the prompt.  A provider "claude" has 3 different interfaces available, sdk, API, cli. We can pipe through cli just fine, we just need feedback and a clean chain of custody for stdio.  

