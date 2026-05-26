---
id: tests.extends-stdlib
extends: stdlib.run-command.task
inputs:
  command:
    default: "echo from-stdlib"
---

# Extends stdlib

Inherits `stdlib.run-command.task`'s run blocks; no additional fences needed.
