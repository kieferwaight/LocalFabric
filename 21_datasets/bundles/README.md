# 21_datasets/bundles/

← [Up to 21_datasets](../README.md)

Curated multi-item test suites. A bundle is a named, versioned set of
dataset members and the acceptance criteria for running a task against
them. Bundles never duplicate binary data — they only reference dataset
IDs declared elsewhere under `21_datasets/`.

## Naming

```
<scope>.<purpose>.bundle.yaml         # On-disk filename
<scope>.<purpose>.bundle              # Manifest id (filename without .yaml)
```

Examples: `vision.smoke.bundle`, `pdf.extraction.regression.bundle`,
`embeddings.chunker.acceptance.bundle`.

## Bundle shape

```yaml
- id: vision.smoke.bundle
  title: <one-line purpose>
  description: |
    What this bundle pins, when it is run, what counts as pass / fail.
  tags: [dataset, bundle, vision]
  extends: stdlib.base

  scope:                       # Which task(s) this bundle exercises
    tasks:
      - image.vision.overview.task
      - image.vision.layout.task

  members:                     # Dataset IDs (NOT file paths)
    - image.photo.example-placeholder.001.dataset

  acceptance:                  # Optional pass/fail thresholds
    pass_rate_min: 1.0         # Every member must pass
    per_member:
      - id: image.photo.example-placeholder.001.dataset
        must_contain: ["palm", "ocean"]

  determinism:
    require_sha_match: true    # Refuse to run if any member's bytes drifted
```

## Local content

See [`vision.smoke.bundle.yaml`](vision.smoke.bundle.yaml) for a worked example.
