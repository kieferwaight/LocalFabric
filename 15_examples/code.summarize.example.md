---
id: code.summarize.example
title: Summarize code with the Claude CLI
description: Summarizes code by piping a prompt into the `claude` CLI binary. Accepts either a `file_path` or inline `input` text.
inputs:
  file_path:
    type: string
    required: false
    default: ""
  input:
    type: string
    required: false
    default: ""
---

# Summarize code

```bash {id: summarize}
file="{{ file_path }}"
if [ -n "$file" ]; then
  source_text=$(cat "$file")
else
  source_text=$(cat <<'LF_INPUT_EOF'
{{ input }}
LF_INPUT_EOF
)
fi

if [ -z "$source_text" ]; then
  echo "code.summarize.example: provide --file_path=<path> or --input=<text>" >&2
  exit 2
fi

claude --model claude-sonnet-4-6 -p "$(cat <<PROMPT_EOF
You are a senior engineer. Summarize the following code clearly and concisely:

$source_text
PROMPT_EOF
)"
```
