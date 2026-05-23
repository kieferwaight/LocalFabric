# Prompts

Prompt templates and role definitions used across the system. Organized by
responsibility, matching `REPO_STRUCTURE.md`.

## Layout

- `roles/` — persona and system-prompt definitions (e.g. "senior reviewer",
  "research assistant"). Use these to set model behavior independent of any
  specific task.
- `tasks/` — task-specific prompt templates (e.g. summarization, extraction,
  classification). Parameterized for reuse.
- `agents/` — composite prompts for multi-step or tool-using agents. Typically
  combine a role plus task instructions plus tool descriptions.
- `templates/` — generic, reusable prompt fragments (few-shot blocks, output
  schemas, chain-of-thought scaffolds) that other prompts can compose.

## Conventions

- Plain Markdown or Jinja-style templates; one prompt per file.
- File name describes purpose, not the model it targets.
- Keep prompts provider-agnostic — model-specific tuning belongs in the
  harness layer, not here.
