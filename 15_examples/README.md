# 15_examples/

Runnable example compositions for the YAML and markdown runtimes. Holds
both:

- **YAML examples** (`*.yaml`) — multi-step compositions exercising mixins,
  inputs, and templated outputs.
- **Markdown examples** (`*.example.md`) — single-prompt fixtures for the
  markdown runtime harness; loaded by the same harness that registers
  `12_prompts/`.

Examples are NOT auto-loaded by `stdlib.load-modules.workflow`. The YAML
runtime picks them up via `import_repo_wide` (which scans this bucket),
and the markdown harness picks up the `.example.md` files the same way.

Naming follows the platform-wide pattern: every concrete id ends with
`.example` (or `.mixin` when the def is a reusable mixin supporting an
example).

| File                               | Id(s)                                                                                       |
| ---------------------------------- | ------------------------------------------------------------------------------------------- |
| `cloud.yaml`                       | `cloud.mixin.git-info`, `cloud.mixin.timestamp`, `cloud.deployer.example`                   |
| `git.yaml`                         | `git.init.example`, `git.github.example`, `git.gitignore.example`                           |
| `obsidian.daily-note.example.yaml` | `obsidian.daily-note.example`                                                               |
| `examples.catalog.yaml`            | `examples.catalog.modules` (manifest, loads all of the above)                               |
| `code.summarize.example.md`        | `code.summarize.example` (provider-style: Claude)                                           |
| `polyglot.hello.example.md`        | `polyglot.hello.example` (fence-style demo)                                                 |
| `python.hello.example.md`          | `python.hello.example` (fence-style demo)                                                   |
| `shell.hello.example.md`           | `shell.hello.example` (fence-style demo, used by `16_tests/harnesses.markdown.cli.test.py`) |
