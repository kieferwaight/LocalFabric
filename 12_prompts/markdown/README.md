# Markdown harness assets

Prompt-template-style markdown that the markdown runtime harness compiles
into YAML runtime definitions.

- `examples/` — committed runnable demos. Used both as documentation and as
  integration test fixtures by `16_tests/harnesses_markdown/`. Includes
  fence-style polyglot demos and a provider-style demo
  (`summarize-code.md`) that routes to Claude via
  `harnesses.markdown.providers.ClaudeProvider`.

The harness lives at `04_harnesses/markdown/`. See its README for the file
format and CLI invocation.
