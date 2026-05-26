---
id: python.hello.example
title: Hello Python
inputs:
  name:
    type: string
    default: world
---

# Hello Python

```python {id: greet}
import os, json
name = "{{ name }}"
print(f"Hello, {name}!")
json.dump({"greeted": name}, open(os.environ["STATE_FILE"], "w"))
```
