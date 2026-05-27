# 21_datasets/data/

← [Up to 21_datasets](../README.md)

Structured-data samples for parsing, schema-validation, and ingest
regression tests. Each file has a sibling `*.dataset.yaml`.

## Children (subclasses)

| Subclass               | Purpose                                                                       |
| ---------------------- | ----------------------------------------------------------------------------- |
| [`json/`](json/)       | Single-object / single-array JSON documents.                                  |
| [`jsonl/`](jsonl/)     | Newline-delimited JSON corpora — chunks, logs, event streams.                 |
| [`csv/`](csv/)         | Tabular CSV samples — headers required; record `media.delimiter` if not `,`.  |

## Conventions

- **Extensions**: `.json`, `.jsonl`, `.csv`.
- **Manifests** record `media.bytes`, `media.sha256`, `media.row_count`
  (for `csv`/`jsonl`), and `media.schema` (link to a `03_schemas/*.schema.yaml`
  when one applies).
- **`class:` field MUST be `data`**, `subclass:` MUST match the subdirectory.

See [`../README.md`](../README.md) for the master manifest contract.
