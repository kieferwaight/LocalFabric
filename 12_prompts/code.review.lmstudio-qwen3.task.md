---
id: code.review.lmstudio-qwen3.task
description: Senior-engineer code review (via LM Studio, Qwen3 27B).
provider: lmstudio
model: qwen/qwen3.6-27b
max_tokens: 1500
temperature: 0.2
inputs:
  source_text:
    type: string
    required: true
---

Review the code below as a senior engineer. Cover:

- Bugs or logic errors
- Security concerns (injection, auth, secrets, unsafe deserialization)
- Performance issues (unnecessary allocations, N+1 queries, hot-path complexity)
- Style and readability
- Test coverage gaps

Format each finding as:

- **Severity** (critical / high / medium / low): one-line description — `file:line` if visible — suggested fix

If the code is clean, say so explicitly and stop.

## Code

{{ source_text }}
