---
id: code.review.gemini-cli.task
description: Senior-engineer code review (via Gemini CLI).
provider: gemini_cli
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
