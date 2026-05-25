---
id: tests.extends-stdlib
extends: stdlib.run-command
inputs:
  command:
    default: "echo from-stdlib"
---

# Extends stdlib

Inherits `stdlib.run-command`'s run blocks; no additional fences needed.
