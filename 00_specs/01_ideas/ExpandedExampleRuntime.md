# Example Expansion System

I dont really like the 15_examples folder, and I would like to make examples be a little more useful.

## Current Task Definition System

Here is an example of a typical task definition

````yaml (Original task)
- id: image.classify.task
  title: Classify an image by semantic type
  description: |
    Classify an image into one of 10 semantic types (photograph, screenshot,
    diagram, chart, infographic, illustration, document, blueprint, logo, other)
    with a confidence score. Wraps lib.image.classify.classify_image.
  tags:
  - task
  extends: task.base
  inputs:
    path:
      type: string
      required: true
      description: Path to the image file.
  run:
  - python: |-
      import json, os
      from pathlib import Path
      from lib.image.classify import classify_image
      result = classify_image(Path("{{ path }}"))
      with open(os.environ["STATE_FILE"], "w") as f:
          json.dump(result, f)
````

and we run it with

`lfc run ./image.classify.task.yaml --image_path=./image.jpg`

## Proposed

I want to expand this task file to include examples.  I want to create a new type of definition class. I want it to follow our current and string taxonomy patterns. So please do a careful review of the best naming pattern. Do not take my suggestions at face value, they are purely conceptual. Perhaps runtime.example.base,  or example.runtime.mixin.  or task.examble.base and workflow.example.base

### Usage

Applying examples would look like this.

```yaml (Task from examples)
##############################
# Original Definition
##############################
- id: image.classify.task
  title: Classify an image by semantic type
  description: |
    Classify an image into one of 10 semantic types (photograph, screenshot,
    diagram, chart, infographic, illustration, document, blueprint, logo, other)
    with a confidence score. Wraps lib.image.classify.classify_image.
  tags:
  - task
  extends: task.base
  inputs:
    path:
      type: string
      required: true
      description: Path to the image file.
  run:
  - python: |-
      import json, os
      from pathlib import Path
      from lib.image.classify import classify_image
      result = classify_image(Path("{{ path }}"))
      with open(os.environ["STATE_FILE"], "w") as f:
          json.dump(result, f)
  
  #########################################
  # NEW ADDITIONS
  #########################################
  mixins: 
  - task.example.mixin
  examples:
    - id: example.1
      description: Loading a computer screenshot into the vision layout prompt.
      inputs:
        image_path: 21_datasets/image/screenshot/lm-studio-model-explorer.001.dataset.yaml
    # - ... Additional examples here
```

Now we have the ability to run
`lfc run --example example.1 ./image.classify.task.yaml`

### Additional Capabilities

```yaml
  # Other property overrides to create robust examples
  - id: example.2
    description: Same screenshot but with a different model.
    inputs:
      image_path: 21_datasets/image/screenshot/lm-studio-model-explorer.001.dataset.yaml
    model: claude-haiku-4-5
    provider: claude

# a hooks system
- id: example.3
  description: Since examples are sometimes similar to tests, we might want to support setup and teardown style hooks.
  inputs:
    image_path: 21_datasets/image/screenshot/lm-studio-model-explorer.001.dataset.yaml
  hooks:
    before:
      bash: | # run bash
      python: | # run python
    after:
      bash: | # run bash
      python: | # run python
```

## Base Definitions

In order to make this work, we have to build up a definition system that works closely with the task.base.  In the example I proposed
above, I added it as a mixin, but its also possible to sub class under task.base -> task.example.base -> (Your Task with examples)

A possible mixin solution might look like this
```yaml 
id: task.example.mixin
description: A simple mixin that provides runtime examples while allowing the exaples to stay associated with thier original inspiration. This binding makes the examples much more useful in a huge catalog system. Being able to track down an examples relevance makes it almost useless if there is not a connection maintained with the original source. This definition solves that.
inputs:
  example:
    type: integer
    required: false
run:
  - python: |
      # - if example id is passed, then we inject the values
      # - Possible run before hooks
      - ../ continue with child class
      # - Run after hooks
examples:
  - id: example.1
    description: Loading a computer screenshot into the vision layout prompt.
    inputs:
      image_path: 21_datasets/image/screenshot/lm-studio-model-explorer.001.dataset.yaml

  - id: example.2
    description: Same screenshot but with a different model.
    inputs:
      image_path: 21_datasets/image/screenshot/lm-studio-model-explorer.001.dataset.yaml
    model: claude-haiku-4-5
    provider: claude

  - id: example.3
    description: Since examples are sometimes similar to tests, we might want to support setup and teardown style hooks.
    inputs:
      image_path: 21_datasets/image/screenshot/lm-studio-model-explorer.001.dataset.yaml
    hooks:
      before:
        bash: | # run bash
        python: | # run python
      after:
        bash: | # run bash
        python: | # run python
```


