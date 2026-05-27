---
id: code.review.codex-cli.task
description: Senior-engineer code review (via Codex CLI, gpt-5-codex).
provider: codex_cli
model: gpt-5-codex
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
