# 21_datasets/

← [Up to repo root](../README.md)

Deterministic, indexable test datasets for model evaluation. Holds the
images, PDFs, structured-data samples, and curated **bundles** consumed by
regression and acceptance tests against vision / OCR / classification /
embedding / extraction tasks.

Distinct from [`16_tests/fixtures/`](../16_tests/fixtures/), which holds
short-lived YAML/MD fixtures used by harness unit tests. `21_datasets/` is
the long-lived corpus a model is *evaluated against*.

## Children

| Path                          | Holds                                                                  |
| ----------------------------- | ---------------------------------------------------------------------- |
| [`inbox/`](inbox/)            | Staging area — drop unsorted files here, triage into `<class>/<subclass>/` later |
| [`image/`](image/)            | Image samples (photo, screenshot, diagram, document-page)              |
| [`document/`](document/)      | Document samples (PDF, Markdown, plain text)                           |
| [`data/`](data/)              | Structured-data samples (JSON, JSONL, CSV)                             |
| [`bundles/`](bundles/)        | Curated multi-item test suites (`*.bundle.yaml`)                       |
| `datasets.catalog.yaml`       | Master manifest — imports every `*.dataset.yaml` and `*.bundle.yaml`   |

## The contract

Every binary or data file under this bucket is accompanied by a sibling
**dataset manifest** (`<descriptor>.NNN.dataset.yaml`). The manifest is the
authoritative record: id, class/subclass, hash, source, license, labels,
and which tasks consume it. **No file lives here without a manifest** — an
unmanifested file is invisible to the catalog and to `lfc dataset` tooling.

The one exception is [`inbox/`](inbox/) — a staging area where files may
sit without a manifest while awaiting triage. Files in the inbox are not
catalogued, not consumed by any test or bundle, and are expected to be
moved out (with a manifest) promptly. See [`inbox/README.md`](inbox/README.md)
for the triage workflow.

### Class taxonomy

The top-level subdirectory IS the class. Subdirectories within it are the
subclass. Both must appear in the manifest as the `class` and `subclass`
fields. The taxonomy mirrors [`07_lib/classify/media.py`](../07_lib/classify/media.py):

| Class      | Subclasses                                       | Extensions                                |
| ---------- | ------------------------------------------------ | ----------------------------------------- |
| `image`    | `photo`, `screenshot`, `diagram`, `document-page` | `.png .jpg .jpeg .webp .gif .tiff .bmp`  |
| `document` | `pdf`, `markdown`, `text`                        | `.pdf .md .txt`                           |
| `data`     | `json`, `jsonl`, `csv`                           | `.json .jsonl .csv`                       |

### Naming

```
<class>/<subclass>/<descriptor>.NNN.<ext>          # The data file
<class>/<subclass>/<descriptor>.NNN.dataset.yaml   # The manifest, same stem
```

- `<descriptor>` is lower-kebab, descriptive of the content (e.g. `beach-sunset`, `terminal-help-output`).
- `NNN` is a zero-padded counter (`001`, `002`, …) so multiple variants of the
  same descriptor sort lexically and stay deterministic.
- Manifest ID mirrors the on-disk path: `image.photo.beach-sunset.001.dataset`.

### Manifest shape

Every `*.dataset.yaml` is a single-document YAML list with one entry that
extends `stdlib.base`. Required keys:

```yaml
- id: image.photo.beach-sunset.001.dataset
  title: <one-line label>
  description: |
    Why this sample exists and what behavior it pins.
  tags: [dataset, image, photo]
  extends: stdlib.base

  class: image                 # MUST match the top-level subdirectory
  subclass: photo              # MUST match the second-level subdirectory

  media:
    path: beach-sunset.001.jpg # Relative to this manifest
    sha256: <64 hex chars>     # Verified by `lfc dataset verify`
    bytes: 184321              # File size; mismatch fails verification
    mime: image/jpeg

  source:
    origin: <URL | "local-capture" | "generated">
    license: <SPDX id, e.g. CC0-1.0>
    captured: 2026-01-15       # YYYY-MM-DD

  determinism:
    pinned: true               # If true, sha256 + bytes must match exactly

  labels:                      # Ground-truth annotations. Free-shape per task.
    overview:
      subject: "Sunset over a sandy beach"
      visible_elements: [palm, ocean, sand, sky]

  uses:                        # Which tasks/prompts consume this sample
    - task: image.vision.overview.task
      asserts: subject_contains "beach"
```

Optional keys: `notes`, `aliases`, `redactions`, `derived_from` (link to a
parent dataset id this was cropped/recoloured from).

### Bundles

A **bundle** is a curated set of dataset members exercised together — e.g.
"every image the vision-overview prompt must pass before release." Bundles
live under [`bundles/`](bundles/) and follow the shape in
[`bundles/README.md`](bundles/README.md).

Bundles never duplicate binary data. They only reference dataset IDs and
declare assertions / acceptance thresholds.

## Determinism rules

1. **Every committed data file has a manifest with a real `sha256`.** An
   empty or placeholder hash is rejected.
2. **`determinism.pinned: true` is the default.** A pinned sample's bytes
   must never change in place — produce a new `<descriptor>.NNN+1.dataset`
   instead and deprecate the old one.
3. **No PII, no licensed content without an SPDX entry.** The `source.license`
   field is required.
4. **Manifests are the source of truth for catalog membership.** Files
   without manifests are flagged by `lfc dataset audit` (planned tooling).

## How indexing works

`datasets.catalog.yaml` is the master manifest — it lists every
`*.dataset.yaml` and `*.bundle.yaml` via its `modules:` array. When loaded
into the YAML runtime, every member becomes a discoverable definition with
its declared id. Future tooling (`lfc dataset list / describe / verify /
audit`) reads the catalog rather than re-walking the filesystem.

## Adding a new sample — two paths

**Fast path** — you already know the class, subclass, and license:

1. Drop the data file at `<class>/<subclass>/<descriptor>.NNN.<ext>`.
2. Compute its hash: `shasum -a 256 path/to/file` (or `uv run lfc task run files.sha256.task --path=<path>`).
3. Author `<descriptor>.NNN.dataset.yaml` with all required fields.
4. Append the manifest path to `datasets.catalog.yaml` under `modules:`.
5. If the sample joins a bundle, append its id to the relevant `*.bundle.yaml`.
6. Update the parent `README.md` children table if you introduced a new subclass directory.

**Inbox path** — you have a file but haven't classified or licensed it yet:

1. Drop the file into [`inbox/`](inbox/) (optionally beside a `*.drop.yaml` note).
2. Follow the triage workflow in [`inbox/README.md`](inbox/README.md), which
   ends by `git mv`-ing the file into its proper `<class>/<subclass>/` location
   alongside a freshly-authored manifest.

Both paths converge on the same outcome: a data file + manifest pair under a
class/subclass directory, registered in `datasets.catalog.yaml`.
