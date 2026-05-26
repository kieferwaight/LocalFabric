# 15_examples/

Example and demo YAML definitions showing how to compose the YAML runtime. These files
are NOT auto-loaded by `stdlib.load-modules.workflow`; load them explicitly via `modules:` or
`runtime.import_yaml(...)` when exercising examples.

| File | What it shows |
|------|---------------|
| `cloud.yaml` | Mixin-composed deployment workflow with `cloud.deployer` |
| `git.yaml` | Git workspace initialization examples |
| `obsidian.yaml` | Obsidian daily-note template example |
| `examples.catalog.yaml` | Module catalog that imports all example definitions |
