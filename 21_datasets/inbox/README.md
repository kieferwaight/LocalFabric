# 21_datasets/inbox/

← [Up to 21_datasets](../README.md)

Staging area for new test data. Drop any file here — image, PDF, data
file, whatever — and triage it into the catalogued layout later. Files
in the inbox are **not** part of the dataset catalog and are **not**
consumed by any test or bundle until they have been classified and
moved.

This is the only location under `21_datasets/` where the
"every-file-has-a-manifest" rule does not apply. The inbox exists
precisely so that contributors can capture an interesting sample
without first having to author its manifest.

## What belongs here

- A sample you want to add to the corpus but haven't yet classified.
- A file that needs license / provenance research before it can be committed.
- A batch of related samples awaiting a triage pass.
- A draft variant that may or may not earn a real entry.

## What does NOT belong here

- Long-lived samples — the inbox is staging, not storage. Triage promptly.
- Anything covered by an existing dataset id — link or update the existing entry instead.
- Build artifacts, scratch outputs, or anything that isn't meant to become a dataset. Those go to [`14_data/`](../../14_data/).
- Secrets, credentials, PII. The inbox has the same review bar as a public commit.

## Triage workflow

Per dropped file:

1. **Inspect** — open the file. Identify which top-level class fits:
   - Image → `image/`
   - Document → `document/`
   - Structured data → `data/`
   The same extension taxonomy used by
   [`07_lib/classify/media.py`](../../07_lib/classify/media.py) is the
   source of truth. Use `uv run lfc task run classify.media.class-for-path.task --path=<inbox-path>`
   if you want the classifier's recommendation.

2. **Pick a subclass** from the parent README's table:
   [`image/README.md`](../image/README.md),
   [`document/README.md`](../document/README.md),
   [`data/README.md`](../data/README.md).
   Add a new subclass directory only if no existing one fits, and update the
   class README children table when you do.

3. **Hash + size**:

   ```
   uv run lfc task run files.sha256.task --path=21_datasets/inbox/<file>
   wc -c 21_datasets/inbox/<file>
   ```

4. **Author the manifest** at the destination — `<class>/<subclass>/<descriptor>.NNN.dataset.yaml` —
   following the shape in [`../README.md`](../README.md). Fill in every required
   field (`class`, `subclass`, `media.{path,sha256,bytes,mime}`, `source.{origin,license}`).

5. **Move the data file** to sit alongside its manifest:

   ```
   git mv 21_datasets/inbox/<file> 21_datasets/<class>/<subclass>/<descriptor>.NNN.<ext>
   ```

   Use `git mv` so history follows the rename.

6. **Register** the new manifest by appending its path to
   [`../datasets.catalog.yaml`](../datasets.catalog.yaml) under `modules:`.

7. **Bundles** — if the new sample belongs to a curated suite, add its id to
   the relevant `bundles/*.bundle.yaml`.

8. **Verify** — confirm the catalog still loads cleanly:

   ```
   uv run python -c "import yaml, pathlib; yaml.safe_load(pathlib.Path('21_datasets/datasets.catalog.yaml').read_text())"
   ```

## Optional drop note

If you need to capture provisional context before triage (where the file came
from, suspected license, why you want it in the corpus), drop a sibling
`<descriptor>.drop.yaml` next to the file:

```yaml
- id: drop.<descriptor>
  origin: <URL | screenshot | "captured by <person>" | "received from <source>">
  license_intent: <SPDX id you expect to use>
  notes: |
    Free-form. Used during triage; deleted once the real *.dataset.yaml is authored.
  dropped: '2026-05-26'
```

Drop notes are NOT registered in `datasets.catalog.yaml` and have no required
shape beyond the keys above. They are a hand-off device between the dropper
and the triager, nothing more. Delete the drop note when the real manifest is
in place.

## Hygiene

- The inbox should be empty most of the time. Anything stuck here longer than
  a single working session is a signal to either triage it or delete it.
- Tooling (`lfc dataset audit`, planned) will flag inbox files older than a
  configurable threshold so they don't rot indefinitely.
- Do not let the inbox accumulate sub-trees. If you find yourself building
  hierarchy inside `inbox/`, that's the moment to triage the whole batch out
  to its proper home.
