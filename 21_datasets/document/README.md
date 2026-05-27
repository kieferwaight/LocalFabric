# 21_datasets/document/

← [Up to 21_datasets](../README.md)

Document samples for PDF extraction, markdown-format compliance, and
text-classification tasks. Each file has a sibling `*.dataset.yaml`.

## Children (subclasses)

| Subclass                    | Purpose                                                                |
| --------------------------- | ---------------------------------------------------------------------- |
| [`pdf/`](pdf/)              | PDFs for `lib.pdf.*` tasks (page count, text extraction, render).      |
| [`markdown/`](markdown/)    | Markdown sources for format-compliance and parsing regression tests.   |
| [`text/`](text/)            | Plain-text corpora — short and long passages for embedding / chunking. |

## Conventions

- **Extensions**: `.pdf`, `.md`, `.txt`.
- **Manifests** record `media.bytes`, `media.sha256`, `media.page_count`
  (PDFs only), and `media.word_count` where relevant.
- **`class:` field MUST be `document`**, `subclass:` MUST match the
  subdirectory.

See [`../README.md`](../README.md) for the master manifest contract.
