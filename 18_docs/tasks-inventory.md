# Tasks inventory

_Regenerated 2026-05-26 after `07_tasks → 07_lib` rename and YAML task-wrapper authoring._

Two complementary layers:

- **`07_lib/`** — Python helper library; import via `lib.*`. Pure(-ish) functions and classes; no workflow orchestration.
- **`07_tasks/`** — YAML task wrappers; each file contains one definition that `extends: task.base` and delegates to a `lib.*` function in its `run:` block.

Workflows under `06_workflows/` compose tasks into pipelines.

---

## Section A — What Python helpers are available (`lib.*`)

### `lib.audit` — boundary-violation audit for the numeric workspace layout

#### `lib.audit.scan_boundary_violations`

- **Purpose:** Find responsibility-boundary violations across the repo; emit one JSON finding per violation.
- **Public:**
  - `iter_audited_files(workspace: Path, output_dir: Path) -> list[Path]` — collect all auditable source files, excluding generated output and archive buckets.
  - `audit_file(path: Path, workspace: Path, generated_at: str) -> list[dict[str, Any]]` — apply per-file heuristic rules and return a list of finding dicts.
  - `audit_cross_file(workspace: Path, generated_at: str) -> list[dict[str, Any]]` — apply cross-file rules (e.g. duplicate Docker lifecycle paths) and return findings.
  - `run_audit(workspace: Path, output_dir: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]` — orchestrate a full audit pass; returns `(findings, summary)`.
  - `preserve_statuses(findings: list[dict[str, Any]], previous_jsonl: Path) -> None` — carry reviewed statuses forward from a prior run's JSONL file.
  - `main() -> None` — CLI entry point; calls `run_audit`, writes `findings.jsonl` and `summary.json`.
- **Notes:** Finding IDs are stable SHA-256 hashes of `{file_path}::{rule}`; safe to carry status across re-runs.

---

### `lib.browser` — web fetch and search-result scraping

#### `lib.browser.fetch_text`

- **Purpose:** Fetch readable page text from a URL or a DuckDuckGo Lite search-results page.
- **Public:**
  - `target_url(topic_or_url: str) -> tuple[str, str]` — return the URL to retrieve and a human-readable source label (`"url"` or `"duckduckgo-lite"`).
  - `fetch_readable_text(topic_or_url: str) -> tuple[str, str, str]` — retrieve, strip scripts/styles, and clean the text; returns `(clean_text, source_label, url)`.
- **Constants:** `TEXT_CAP = 8000` (character cap on returned text), `HEADERS` (default User-Agent).

---

### `lib.classify` — file classification and manifest building

#### `lib.classify.media`

- **Purpose:** Classify files by broad media class and content-routing category.
- **Public:**
  - `media_class_for_path(path: Path) -> str` — return `"image"`, `"document"`, or `"unknown"` for ingest routing.
  - `classify_file(rel_path: Path) -> dict` — return `{class, subclass, recommended_destination, confidence, reason}` based on extension and path prefix rules.
- **Constants:** `DOC_EXT`, `CODE_EXT`, `DATA_EXT`, `IMAGE_EXT`, `ARCHIVE_EXT` — module-level extension sets available for import.

#### `lib.classify.build_manifest`

- **Purpose:** Walk a root directory and produce three classification/state reports.
- **Public:**
  - `build_classification(root: Path) -> tuple[dict, dict, dict]` — return `(classification_report, current_state_manifest, fingerprint_report)` after walking *root* with `classify_file`, `sha256_file`, and `infer_source_guess`.
- **Constants:** `CONFIDENCE_REVIEW_THRESHOLD = 0.80`.

---

### `lib.embeddings` — local embedding pipeline

#### `lib.embeddings.chunker`

- **Purpose:** Split source files into embeddable text chunks using AST (Python) or sliding-window (everything else) strategies.
- **Public:**
  - `chunk_file(path: str) -> list[dict]` — read a file and return chunk dicts; each dict contains `{text, source, chunk_index, line_start, line_end, strategy}`.
- **Constants:** `WINDOW_TOKENS = 512`, `OVERLAP_RATIO = 0.10`, `CHARS_PER_TOKEN = 4`, `SLIDING_WINDOW_EXTS`.

#### `lib.embeddings.embedder`

- **Purpose:** Generate and cache embeddings by delegating to an `EmbeddingExecutor` (default: `OllamaHarness`) and persisting vectors in a `JsonCache`.
- **Public:**
  - `EmbeddingExecutor` — `Protocol` defining `embed(text, model) -> list[float]`.
  - `EmbedderUnavailable` — `RuntimeError` subclass raised when embedding cannot complete.
  - `Embedder` — class with:
    - `__init__(model, cache_path, batch_size, executor)` — inject executor and cache driver.
    - `embed(text: str, bypass_cache: bool = False) -> list[float]` — embed a single text, consulting the cache first.
    - `embed_chunks(chunks: list[dict], bypass_cache, verbose) -> list[dict]` — attach `"vector"` keys to chunk dicts in place.
    - `cache_stats() -> dict` — return `{entries, path, model}`.
    - `flush_cache() -> None` — force a cache write.
    - `clear_cache() -> None` — wipe cache in memory and on disk.

#### `lib.embeddings.query`

- **Purpose:** High-level query interface: embed a text query and retrieve top-k chunks from the vector store as a formatted markdown context block.
- **Public:**
  - `LocalKnowledgeQuery` — class with:
    - `__init__(backend, store_path, model, k)` — initialise with `"lancedb"` (default) or `"numpy"` backend.
    - `query(query_text: str, k, source_filter, min_score, as_markdown) -> str | list[dict]` — embed and retrieve; returns markdown string or raw list.
    - `store` (property) — exposes the underlying `VectorStore`.
    - `embedder` (property) — exposes the underlying `Embedder`.

#### `lib.embeddings.sweep`

- **Purpose:** Atomic helpers for directory walking, file hashing, and manifest I/O used by `06_workflows/embeddings.sweep.workflow.yaml`.
- **Public:**
  - `collect_files(root: str) -> list[str]` — walk *root* respecting `SKIP_DIRS` and `INDEXED_EXTENSIONS`; return sorted paths.
  - `file_hash(path: str) -> str` — return the MD5 hex digest of a file.
  - `load_manifest(manifest_path: str) -> dict[str, str]` — load the JSON sweep manifest, returning `{}` on missing/corrupt.
  - `save_manifest(manifest_path: str, manifest: dict[str, str]) -> None` — persist the manifest as JSON.
- **Constants:** `INDEXED_EXTENSIONS`, `SKIP_DIRS`.

---

### `lib.files` — file-walking and hashing helpers

#### `lib.files` (top-level module at `07_lib/files.py`)

- **Purpose:** Shared utilities for walking a directory tree and hashing files; used by classification and ingest scripts.
- **Public:**
  - `iter_files(root: Path = REPO_ROOT) -> Iterable[Path]` — yield files under *root*, skipping excluded dirs, protected inboxes, and backup prefixes.
  - `sha256_file(path: Path) -> str` — return the SHA-256 hex digest of a file.
  - `write_json(path: Path, data: object) -> None` — write *data* as indented JSON, creating parent dirs as needed.
- **Constants:** `IMAGE_EXTENSIONS`, `IGNORED_DIR_NAMES`, `IGNORED_FILE_NAMES`, `EXCLUDED_PREFIXES`, `PROTECTED_INBOX_SUBPATHS`.
- **Note:** Top-level module (`lib.files`), not a sub-package. Import directly as `from lib.files import iter_files`.

---

### `lib.image` — image signal extraction

#### `lib.image.classify`

- **Purpose:** Classify an image into one of 10 semantic types using CV2 signals.
- **Public:**
  - `classify_image(path: Path) -> dict` — return `{kind, confidence, scores}` where `kind` is one of `photograph`, `screenshot`, `diagram`, `chart`, `infographic`, `illustration`, `document`, `blueprint`, `logo`, `other`.

#### `lib.image.color`

- **Purpose:** Extract dominant colour palette, brightness, contrast, and saturation.
- **Public:**
  - `extract_color(path: Path, n_colors: int = 6) -> dict` — return `{palette, dominant_hex, brightness, contrast, saturation}`; palette built by k-means over a 150×150 thumbnail.

#### `lib.image.meta`

- **Purpose:** Extract file identity metadata, pixel dimensions, EXIF, and ICC profile info.
- **Public:**
  - `extract_meta(path: Path) -> dict` — return `{sha256, size_bytes, filename, extension, mime_type, width, height, mode, format, has_exif, exif, has_icc, icc_description}`.

#### `lib.image.quality`

- **Purpose:** Assess image quality via blur score, edge density, and near-blank detection.
- **Public:**
  - `extract_quality(path: Path) -> dict` — return `{blur_score, is_blurry, edge_density, is_blank, mean_brightness, brightness_std}`.

#### `lib.image.regions`

- **Purpose:** Detect visible content regions, OCR text bounding boxes, and graphic contours.
- **Public:**
  - `extract_regions(path: Path, max_contours: int = 20) -> dict` — return `{content_bbox, ocr_regions, contours, image_width, image_height}`; OCR regions require `pytesseract` (skipped gracefully if absent).

#### `lib.image.text_ocr`

- **Purpose:** Full OCR text extraction with per-word bounding boxes and block groupings.
- **Public:**
  - `extract_text(path: Path) -> dict` — return `{full_text, word_count, words, blocks}`; requires `pytesseract`; returns empty structure with `"error"` key on failure.

---

### `lib.metadata` — file metadata inference

#### `lib.metadata.extract`

- **Purpose:** Infer source provenance and document type from file path and name heuristics.
- **Public:**
  - `infer_source_guess(rel_path: Path) -> str` — return a source label (`"gemini"`, `"openai"`, `"perplexity"`, `"undermind"`, `"manual"`, `"scraped"`, `"uploads"`, or `"unknown"`) based on path parts.
  - `infer_doc_type(name: str) -> str` — return `"report"`, `"prompt"`, `"specification"`, `"draft"`, or `"note"` based on filename keywords.

---

### `lib.pdf` — PDF inspection

#### `lib.pdf.meta`

- **Purpose:** PDF-specific metadata extraction utilities (currently page count via `pdfinfo`).
- **Public:**
  - `page_count(path: Path) -> int | None` — return the page count using the `pdfinfo` CLI tool; returns `None` when `pdfinfo` is unavailable or fails.

---

### `lib.research` — local research and summarization

#### `lib.research.local_summarize`

- **Purpose:** Fetch readable web content and summarize it through the local Ollama harness using a markdown prompt template.
- **Public:**
  - `local_research_scaffold(topic_or_url: str, harness: OllamaHarness | None = None) -> str` — fetch text via `lib.browser.fetch_text`, pick the best available local model, and return a summarized string (falls back to raw text when Ollama is unavailable). Pass `harness` to inject a fake in tests or reuse a pre-configured harness across calls.

---

### `lib.shell` — shell-backed utility tasks

#### `lib.shell.run_tests`

- **Purpose:** Execute a local test command and return a compact trimmed report string.
- **Public:**
  - `run_local_tests(command: str = "pytest") -> str` — run *command* in a subprocess (30 s timeout) and return a `SUCCESS`/`FAILURE` string with trimmed output.

---

### `lib.text` — text formatting helpers

#### `lib.text.format_markdown`

- **Purpose:** Reformat a markdown document via an LM Studio harness using a prompt template.
- **Public:**
  - `load_prompt() -> str` — read and parse the `tasks.format-markdown.md` prompt template.
  - `format_markdown_with_lmstudio(file_path: str, model: str = "qwen/qwen3.6-27b", executor: _MarkdownExecutor | None = None) -> str` — read *file_path*, inject content into the prompt, and return the reformatted text. Pass `executor` to inject a fake in tests (avoids LM Studio network call).

---

### Section A summary

| Subsystem        | Modules | Public functions / methods | Public classes/protocols |
|------------------|---------|---------------------------|--------------------------|
| `lib.audit`      | 1       | 6                         | 0                        |
| `lib.browser`    | 1       | 2                         | 0                        |
| `lib.classify`   | 2       | 3                         | 0                        |
| `lib.embeddings` | 4       | 10                        | 3                        |
| `lib.files`      | 1       | 3                         | 0                        |
| `lib.image`      | 6       | 6                         | 0                        |
| `lib.metadata`   | 1       | 2                         | 0                        |
| `lib.pdf`        | 1       | 1                         | 0                        |
| `lib.research`   | 1       | 1                         | 0                        |
| `lib.shell`      | 1       | 1                         | 0                        |
| `lib.text`       | 1       | 2                         | 1                        |
| **Total**        | **20**  | **37**                    | **4**                    |

---

## Section B — What tasks can I invoke (`07_tasks/*.task.yaml`)

Each entry shows the task id, its required inputs, and the `lib.*` function it delegates to.

### `audit.*`

| Task id | Inputs | Delegates to |
|---------|--------|--------------|
| `audit.boundary_violations.scan.task` | `workspace`, `output_dir` | `lib.audit.scan_boundary_violations.run_audit` |

### `browser.*`

| Task id | Inputs | Delegates to |
|---------|--------|--------------|
| `browser.fetch.text.task` | `topic_or_url` | `lib.browser.fetch_text.fetch_readable_text` |

### `classify.*`

| Task id | Inputs | Delegates to |
|---------|--------|--------------|
| `classify.manifest.build.task` | `root`, `output_dir` | `lib.classify.build_manifest.build_classification` |
| `classify.media.class_for_path.task` | `path` | `lib.classify.media.media_class_for_path` |
| `classify.media.file.task` | `rel_path` | `lib.classify.media.classify_file` |

### `embeddings.*`

| Task id | Inputs | Delegates to |
|---------|--------|--------------|
| `embeddings.chunker.chunk_file.task` | `path` | `lib.embeddings.chunker.chunk_file` |
| `embeddings.embed.text.task` | `text`, `model` | `lib.embeddings.embedder.Embedder.embed` |
| `embeddings.query.search.task` | `query_text`, `k`, `model`, `as_markdown` | `lib.embeddings.query.LocalKnowledgeQuery.query` |
| `embeddings.sweep.collect_files.task` | `root` | `lib.embeddings.sweep.collect_files` |
| `embeddings.sweep.file_hash.task` | `path` | `lib.embeddings.sweep.file_hash` |
| `embeddings.sweep.load_manifest.task` | `manifest_path` | `lib.embeddings.sweep.load_manifest` |
| `embeddings.sweep.save_manifest.task` | `manifest_path`, `manifest` | `lib.embeddings.sweep.save_manifest` |

### `files.*`

| Task id | Inputs | Delegates to |
|---------|--------|--------------|
| `files.iter.task` | `root` | `lib.files.iter_files` |
| `files.sha256.task` | `path` | `lib.files.sha256_file` |
| `files.write_json.task` | `path`, `data` | `lib.files.write_json` |

### `image.*`

| Task id | Inputs | Delegates to |
|---------|--------|--------------|
| `image.classify.task` | `path` | `lib.image.classify.classify_image` |
| `image.color.dominant.task` | `path`, `n_colors` | `lib.image.color.extract_color` |
| `image.meta.extract.task` | `path` | `lib.image.meta.extract_meta` |
| `image.quality.extract.task` | `path` | `lib.image.quality.extract_quality` |
| `image.regions.extract.task` | `path`, `max_contours` | `lib.image.regions.extract_regions` |
| `image.text_ocr.extract.task` | `path` | `lib.image.text_ocr.extract_text` |

### `metadata.*`

| Task id | Inputs | Delegates to |
|---------|--------|--------------|
| `metadata.doc_type.task` | `name` | `lib.metadata.extract.infer_doc_type` |
| `metadata.source_guess.task` | `rel_path` | `lib.metadata.extract.infer_source_guess` |

### `pdf.*`

| Task id | Inputs | Delegates to |
|---------|--------|--------------|
| `pdf.meta.page_count.task` | `path` | `lib.pdf.meta.page_count` |

### `research.*`

| Task id | Inputs | Delegates to |
|---------|--------|--------------|
| `research.local.summarize.task` | `topic_or_url` | `lib.research.local_summarize.local_research_scaffold` |

### `shell.*`

| Task id | Inputs | Delegates to |
|---------|--------|--------------|
| `shell.tests.run.task` | `command` | `lib.shell.run_tests.run_local_tests` |

### `text.*`

| Task id | Inputs | Delegates to |
|---------|--------|--------------|
| `text.markdown.format.task` | `file_path`, `model` | `lib.text.format_markdown.format_markdown_with_lmstudio` |

### Section B summary

27 task wrappers across 11 domains. Every public `lib.*` function that represents a complete atomic operation has a corresponding `.task.yaml`.

---

## Section C — Cross-reference (lib function ↔ YAML task)

| `lib.*` function / method | Task id |
|---------------------------|---------|
| `lib.audit.scan_boundary_violations.run_audit` | `audit.boundary_violations.scan.task` |
| `lib.browser.fetch_text.fetch_readable_text` | `browser.fetch.text.task` |
| `lib.classify.build_manifest.build_classification` | `classify.manifest.build.task` |
| `lib.classify.media.classify_file` | `classify.media.file.task` |
| `lib.classify.media.media_class_for_path` | `classify.media.class_for_path.task` |
| `lib.embeddings.chunker.chunk_file` | `embeddings.chunker.chunk_file.task` |
| `lib.embeddings.embedder.Embedder.embed` | `embeddings.embed.text.task` |
| `lib.embeddings.query.LocalKnowledgeQuery.query` | `embeddings.query.search.task` |
| `lib.embeddings.sweep.collect_files` | `embeddings.sweep.collect_files.task` |
| `lib.embeddings.sweep.file_hash` | `embeddings.sweep.file_hash.task` |
| `lib.embeddings.sweep.load_manifest` | `embeddings.sweep.load_manifest.task` |
| `lib.embeddings.sweep.save_manifest` | `embeddings.sweep.save_manifest.task` |
| `lib.files.iter_files` | `files.iter.task` |
| `lib.files.sha256_file` | `files.sha256.task` |
| `lib.files.write_json` | `files.write_json.task` |
| `lib.image.classify.classify_image` | `image.classify.task` |
| `lib.image.color.extract_color` | `image.color.dominant.task` |
| `lib.image.meta.extract_meta` | `image.meta.extract.task` |
| `lib.image.quality.extract_quality` | `image.quality.extract.task` |
| `lib.image.regions.extract_regions` | `image.regions.extract.task` |
| `lib.image.text_ocr.extract_text` | `image.text_ocr.extract.task` |
| `lib.metadata.extract.infer_doc_type` | `metadata.doc_type.task` |
| `lib.metadata.extract.infer_source_guess` | `metadata.source_guess.task` |
| `lib.pdf.meta.page_count` | `pdf.meta.page_count.task` |
| `lib.research.local_summarize.local_research_scaffold` | `research.local.summarize.task` |
| `lib.shell.run_tests.run_local_tests` | `shell.tests.run.task` |
| `lib.text.format_markdown.format_markdown_with_lmstudio` | `text.markdown.format.task` |

**No gaps**: every public atomic function in `lib.*` has a task wrapper, and every task wrapper corresponds to a real `lib.*` function.

Functions with no task wrapper (intentionally excluded — internal/support use only):
- `lib.browser.fetch_text.target_url` — internal helper called by `fetch_readable_text`
- `lib.audit.scan_boundary_violations.iter_audited_files`, `audit_file`, `audit_cross_file`, `preserve_statuses`, `main` — orchestration internals; `run_audit` is the single public entry point
- `lib.text.format_markdown.load_prompt` — internal loader called by `format_markdown_with_lmstudio`
- `lib.embeddings.embedder.Embedder.embed_chunks`, `cache_stats`, `flush_cache`, `clear_cache` — lifecycle helpers on the `Embedder` class; `embed` is the primary call path
