---
id: code.summarize.example
title: Summarize code with the Claude CLI
description: Summarizes code by streaming a prompt through the `claude` CLI binary. Accepts either a `file_path` or inline `input` text.
inputs:
  file_path:
    type: string
    required: false
    default: ""
  input:
    type: string
    required: false
    default: ""
variables:
  body: ""
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

# Spinner writes to /dev/tty so it never lands in stdout (which the YAML
# dispatcher captures) or in stderr (which it streams). Silently degrades
# to a plain wait when no controlling tty is available (CI, piped runs).
spin() {
  # Note: bash array-length syntax (dollar-brace-hash) clashes with Jinja's
  # comment delimiter; frame count is hardcoded as 10 below.
  local pid=$1 msg=$2 frames=(⠋ ⠙ ⠹ ⠸ ⠼ ⠴ ⠦ ⠧ ⠇ ⠏) i=0
  if ! { : > /dev/tty; } 2>/dev/null; then
    wait "$pid"; return $?
  fi
  printf '\033[?25l' > /dev/tty
  while kill -0 "$pid" 2>/dev/null; do
    printf '\r\033[2K%s %s' "${frames[$((i % 10))]}" "$msg" > /dev/tty
    i=$((i + 1))
    sleep 0.1
  done
  printf '\r\033[2K\033[?25h' > /dev/tty
  wait "$pid"; return $?
}

out=$(mktemp)
trap 'rm -f "$out"' EXIT

claude --model claude-sonnet-4-6 -p "$(cat <<PROMPT_EOF
You are a senior engineer. Summarize the following code clearly and concisely:

$source_text
PROMPT_EOF
)" > "$out" 2>&1 &

spin $! "Asking Claude…"
exit_code=$?

cat "$out" >&2
exit $exit_code
```
