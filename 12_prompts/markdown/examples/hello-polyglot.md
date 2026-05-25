---
id: examples.hello-polyglot
title: Hello Polyglot
inputs:
  name:
    type: string
    required: true
---

# Hello Polyglot

```bash {id: shell-step}
echo "shell sees name={{ name }}"
```

```python {id: py-step}
print("python sees name={{ name }}")
```

```js {id: js-step}
console.log("node sees name={{ name }}")
```
