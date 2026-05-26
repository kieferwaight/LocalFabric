---
id: tests.polyglot
inputs:
  name:
    type: string
    required: true
---

# Polyglot

```bash {id: shell-step}
echo "shell sees {{ name }}"
```

```python {id: py-step}
import os, json
json.dump({"py_saw": "{{ name }}"}, open(os.environ["STATE_FILE"], "w"))
```
