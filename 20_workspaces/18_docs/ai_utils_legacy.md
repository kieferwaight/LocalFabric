# ai_utils (legacy) — Historical README

> Preserved verbatim from the pre-reclassification ai_utils package.
> Paths, script locations, and module references below describe the OLD
> monolithic `ai_utils` layout. The current layout is defined in
> `REPO_STRUCTURE.md` at the repo root, with code under
> `20_workspaces/` organised by responsibility bucket.
>
> Cross-references that still apply (post-migration):
>
> | Legacy reference                              | New location                                       |
> |-----------------------------------------------|----------------------------------------------------|
> | `scripts/prompts/*.py`                        | `20_workspaces/12_prompts/tasks/`                  |
> | `scripts/tools/image/extract-*.py`            | functions in `20_workspaces/07_tools/image/*.py`   |
> | `scripts/workflows/parse-meaning-image.sh`    | `20_workspaces/06_workflows/shell/parse-meaning-image.sh` |
> | `scripts/workflows/parse-meaning-pdf.sh`      | `20_workspaces/06_workflows/shell/parse-meaning-pdf.sh`   |
> | `ai_utils.config`                             | `core.config`                                      |
> | `ai_utils.core.file_utils`                    | `core.file_utils`                                  |
> | `ai_utils.core.metadata`                      | `tools.metadata.extract`                           |
> | `ai_utils.core.classifier`                    | `tools.classify.media`                             |
> | `ai_utils.db.{schema,session}`                | `drivers.sql.{schema,session}`                     |
> | `ai_utils.tasks.image.*`                      | `tools.image.*`                                    |
> | `ai_utils.tasks.vision.ollama`                | `tools.vision.ollama_client`                       |
> | `ai_utils.workflows.types`                    | `workflows.langgraph.types`                        |
> | `ai_utils.workflows.ingest.*`                 | `workflows.langgraph.ingest.*`                     |
> | `ai_utils.workflows.image_intelligence.*`     | `workflows.langgraph.image_intelligence.*`         |
> | `ai_utils.cli.main`                           | `adapters.cli.main` (lives at `20_workspaces/03_adapters/cli/main.py`) |
> | `src/scripts/classify_files.py`               | `20_workspaces/17_scripts/classify_files.py`       |

---

# Scripts

Document and image intelligence tools for the Trash Compactor Monitoring Case Study. All active scripts are Python; the original shell wrappers have been removed.

---

## Structure

```
scripts/
├── prompts/          Ollama LLM prompt wrappers (vision + text)
├── tools/            Standalone extraction tools (each with a paired .md)
│   ├── image/        Image signal extraction (6 tools)
│   ├── pdf/          PDF extraction — PyMuPDF, pdfminer, canonical merge
│   │   ├── pymupdf/
│   │   └── pdfminer/
│   ├── text/         Text utility tools
│   └── docx/         DOCX research notes (no implementation yet)
├── workflows/        End-to-end pipeline scripts
└── test-content/     Fixtures and pre-generated test outputs
```

---

## Prompts (`scripts/prompts/`)

Thin Python wrappers that send a prompt + image to a local Ollama instance.

| Script | Model default | Purpose |
|---|---|---|
| `extract-visible-overview-from-image.py` | `llama3.2-vision` | One-sentence visual overview |
| `extract-visible-layout-from-image.py`   | `llama3.2-vision` | Spatial layout description |
| `extract-visible-style-from-image.py`    | `llama3.2-vision` | Visual style description |
| `extract-visible-text-from-image.py`     | `llama3.2-vision` | Exact visible text extraction |
| `generate-title-from-text.py`            | `mistral:7b-instruct` | Title generation from body text |

All prompts read model and sampling parameters from environment variables. See each file's docstring for the full env-var list.

**Quick use:**
```sh
python scripts/prompts/extract-visible-overview-from-image.py path/to/image.png
```

---

## Image Tools (`scripts/tools/image/`)

Each tool is fully self-contained, stdlib-only beyond its declared deps, and outputs JSON.

| Tool | Output | Deps |
|---|---|---|
| `extract-classify.py` | Image type classification (10 classes) with confidence | pillow, opencv, pytesseract, numpy |
| `extract-color.py`    | Dominant palette, brightness, contrast, saturation | pillow, numpy |
| `extract-meta.py`     | File hash, dimensions, mode, EXIF, ICC profile | pillow |
| `extract-quality.py`  | Blur score, edge density, near-blank flag | pillow, opencv, numpy |
| `extract-regions.py`  | Visible content bbox, OCR regions, graphic contours | pillow, opencv, pytesseract, numpy |
| `extract-text.py`     | Full OCR text, per-word boxes, block groupings | pillow, pytesseract, numpy |

All tools share the same CLI pattern:
```sh
python scripts/tools/image/extract-<signal>.py <image>
python scripts/tools/image/extract-<signal>.py <image> --output result.json
```

See each tool's paired `.md` for full output schema and field descriptions.

---

## PDF Tools (`scripts/tools/pdf/`)

Two-library hybrid approach: PyMuPDF for geometry/color/images, pdfminer.six for reading-order fidelity.

| Tool | Location | Purpose |
|---|---|---|
| `pymupdf/extract.py`        | `pdf/pymupdf/` | Full raw artifact: spans, images, links, annotations, metadata |
| `pymupdf/extract-text.py`   | `pdf/pymupdf/` | Plain text from a PyMuPDF artifact file |
| `pymupdf/extract-tables.py` | `pdf/pymupdf/` | Table candidates from a PyMuPDF artifact file |
| `pymupdf/extract-links.py`  | `pdf/pymupdf/` | Hyperlinks (URI + internal targets) from a PyMuPDF artifact |
| `pymupdf/extract-images.py` | `pdf/pymupdf/` | Extract embedded images to a directory with a manifest |
| `pdfminer/extract.py`       | `pdf/pdfminer/` | Full raw artifact: char geometry, reading order, layout tree |
| `pdfminer/extract-text.py`  | `pdf/pdfminer/` | Plain text from a pdfminer artifact file |
| `pdfminer/extract-tables.py`| `pdf/pdfminer/` | Table candidates from a pdfminer artifact file |
| `convert-png.py`            | `pdf/`          | Render each page to PNG (Poppler via pdf2image) |
| `extract-canonical.py`      | `pdf/`          | Merge both extractors into one flat AI-ready JSONL |

See `tools/pdf/README.md` for the canonical span schema and which output to use for each use case.

---

## Text Tools (`scripts/tools/text/`)

| Tool | Purpose |
|---|---|
| `convert-safe-filename.py` | Convert a title string to a filename-safe slug (optional date prefix, sequence number, extension) |

---

## Workflows (`scripts/workflows/`)

End-to-end pipelines that run multiple tools in parallel and merge results into a single JSON report.

| Script | Input | Output |
|---|---|---|
| `parse-meaning-image.sh` | Image file | `<image-stem>.json` — all 6 image signals + 3 Ollama vision prompts |
| `parse-meaning-pdf.sh`   | PDF file   | `<pdf-stem>.json` — full PDF extraction + first-page image analysis + vision prompts |

```sh
bash scripts/workflows/parse-meaning-image.sh path/to/image.png
bash scripts/workflows/parse-meaning-pdf.sh   path/to/document.pdf
```

The PDF workflow runs in four phases:
- **Phase A (parallel):** PyMuPDF, pdfminer, table extraction, image extraction, canonical merge, PNG render
- **Phase B (parallel):** Text/table/link extraction from artifacts + image analysis on first-page PNG
- **Phase C (sequential):** Ollama vision prompts on first-page PNG
- **Phase D:** Merge everything into a single JSON report

---

## Test Content (`scripts/test-content/`)

Fixture files used during development, with pre-generated outputs stored in `test-content/test-outputs/`.

| Fixture | Type | Notes |
|---|---|---|
| `arduino-system-build-blueprint.png` | Image | Technical diagram |
| `contractor-agreement.pdf`           | PDF   | Multi-page legal document |
| `email-with-many-images.pdf`         | PDF   | Email export with 39 embedded images |
| `example-case-study.pdf`             | PDF   | Reference case study document |
| `exported-email-with-html.pdf`       | PDF   | HTML email rendered to PDF |
| `invoice.pdf`                        | PDF   | Simple invoice |
| `multi-thread-email-with-links-and-missing-images.pdf` | PDF | Complex email thread |
| `W9.pdf`                             | PDF   | IRS tax form |
| `graph.jpeg`                         | Image | Data visualization |
| `logo.jpeg`                          | Image | Brand logo |
| `map.png`                            | Image | Geographic map |
| `picture-with-reciept.jpeg`          | Image | Photo with embedded receipt |
| `profile-photo.jpeg`                 | Image | Portrait photo |
| `web-screenshot.jpeg`                | Image | Browser screenshot |
| `webpage-mockup.jpeg`                | Image | UI mockup |

---

## Dependencies Summary

```sh
pip install pymupdf pdfminer.six pdf2image pillow opencv-python pytesseract numpy
brew install poppler tesseract   # system binaries (macOS)
```

Ollama must be running locally (`http://localhost:11434`) for prompts and workflow vision phases.

---

## Capability Gaps

| Capability | Status |
|---|---|
| DOCX extraction | Research only (`tools/docx/research.md`) — no implementation |
| ExifTool metadata | Documented in research, not yet implemented |
| PaddleOCR (higher-quality OCR) | Documented in research, not yet implemented |
| Perceptual hashing / dedup | Not implemented |
| LLM image card generator | Not implemented |
| Embedding pipeline | Not implemented |
| MIME type detection | Not implemented |
| Audio/video extraction | Out of scope |
