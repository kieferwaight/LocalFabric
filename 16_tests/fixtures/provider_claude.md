---
id: tests.provider-claude
description: Summarizes a code file using Claude
provider: claude
model: claude-sonnet-4-6
inputs:
  input:
    type: string
    required: true
---

You are a senior engineer. Summarize the following code clearly and concisely:

{{ input }}
