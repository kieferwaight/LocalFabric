#!/usr/bin/env bash
# Archived legacy shell workflow for parsing the meaning of a PDF file.
#
# Phase A (parallel)  — raw artifact extraction + direct-PDF tools + PNG render
# Phase B (parallel)  — artifact-dependent tools + image analysis on first page
# Phase C (sequential)— Ollama vision prompts on the first-page PNG
# Phase D             — merge everything into a single JSON report
#
# The JSON report is saved next to the PDF with a .json extension.
# Extracted images are saved to <pdf-stem>-images/ beside the PDF.
#
# Usage:
#   bash 06_workflows/shell/parse-meaning-pdf.sh <pdf>
#
# NOTE: This script expects CLI wrappers for the PDF and image tools
# under 07_tools/{pdf,image}/cli/. The pdf tools (pymupdf/pdfminer/canonical
# extractors) were not part of the ai_utils source tree migrated here —
# they are referenced for reference only. This shell variant is preserved
# as a historical reference.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACES_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# ── tool / prompt locations under the new bucket layout ──────────────────────

PDF_TOOLS="$WORKSPACES_ROOT/07_tools/pdf/cli"
IMAGE_TOOLS_CLI="$WORKSPACES_ROOT/07_tools/image/cli"
PROMPTS="$WORKSPACES_ROOT/12_prompts/tasks"

# ── paths ─────────────────────────────────────────────────────────────────────

PDF="${1:-}"
if [[ -z "$PDF" ]]; then
  echo "Usage: $0 <pdf>" >&2
  exit 1
fi
PDF="$(python3 -c "import pathlib, sys; print(pathlib.Path(sys.argv[1]).resolve())" "$PDF")"

if [[ ! -f "$PDF" ]]; then
  echo "Error: file not found: $PDF" >&2
  exit 1
fi

PDF_DIR="$(dirname "$PDF")"
PDF_STEM="$(basename "${PDF%.*}")"
OUTPUT="$PDF_DIR/$PDF_STEM.json"
IMAGES_DIR="$PDF_DIR/${PDF_STEM}-images"

echo "PDF:    $PDF" >&2
echo "Output: $OUTPUT" >&2

# ── temp workspace ────────────────────────────────────────────────────────────

TMPDIR_WORK="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_WORK"' EXIT
PNG_TMPDIR="$TMPDIR_WORK/png"
mkdir -p "$PNG_TMPDIR"

# ── phase A: parallel direct-PDF tools ───────────────────────────────────────

echo "" >&2
echo "Phase A — raw extraction & PDF render..." >&2

python3 "$PDF_TOOLS/pymupdf/extract.py" \
  "$PDF" "$TMPDIR_WORK/pymupdf.json" &
PID_MU=$!

python3 "$PDF_TOOLS/pdfminer/extract.py" \
  "$PDF" "$TMPDIR_WORK/pdfminer.json" &
PID_PM=$!

python3 "$PDF_TOOLS/pymupdf/extract-tables.py" \
  "$PDF" "$TMPDIR_WORK/pymupdf-tables.json" &
PID_MU_TBL=$!

python3 "$PDF_TOOLS/pymupdf/extract-images.py" \
  "$PDF" "$IMAGES_DIR" &
PID_IMGS=$!

python3 "$PDF_TOOLS/extract-canonical.py" \
  "$PDF" "$TMPDIR_WORK/canonical.jsonl" &
PID_CAN=$!

# convert-png: capture the first output PNG path from stdout
python3 "$PDF_TOOLS/convert-png.py" \
  "$PDF" "$PNG_TMPDIR" > "$TMPDIR_WORK/png-paths.txt" &
PID_PNG=$!

FAILED_A=0
for PID_NAME in \
  "$PID_MU:pymupdf-extract" \
  "$PID_PM:pdfminer-extract" \
  "$PID_MU_TBL:pymupdf-tables" \
  "$PID_IMGS:pymupdf-images" \
  "$PID_CAN:canonical" \
  "$PID_PNG:convert-png"
do
  PID="${PID_NAME%%:*}"; NAME="${PID_NAME##*:}"
  if ! wait "$PID"; then
    echo "  Warning: $NAME failed" >&2
    FAILED_A=$((FAILED_A + 1))
  else
    echo "  Done: $NAME" >&2
  fi
done

[[ $FAILED_A -gt 0 ]] && echo "  ($FAILED_A phase-A tool(s) failed — continuing)" >&2

# Resolve the first-page PNG path
FIRST_PNG="$(head -1 "$TMPDIR_WORK/png-paths.txt" 2>/dev/null || true)"
if [[ -z "$FIRST_PNG" || ! -f "$FIRST_PNG" ]]; then
  echo "  Warning: no PNG rendered — skipping image analysis and vision prompts" >&2
  FIRST_PNG=""
fi

# ── phase B: parallel artifact-dependent + image tools ───────────────────────

echo "" >&2
echo "Phase B — text/tables/links from artifacts + image analysis..." >&2

python3 "$PDF_TOOLS/pymupdf/extract-text.py" \
  "$TMPDIR_WORK/pymupdf.json" "$TMPDIR_WORK/pymupdf-text.txt" &
PID_MU_TXT=$!

python3 "$PDF_TOOLS/pdfminer/extract-text.py" \
  "$TMPDIR_WORK/pdfminer.json" "$TMPDIR_WORK/pdfminer-text.txt" &
PID_PM_TXT=$!

python3 "$PDF_TOOLS/pdfminer/extract-tables.py" \
  "$TMPDIR_WORK/pdfminer.json" "$TMPDIR_WORK/pdfminer-tables.json" &
PID_PM_TBL=$!

python3 "$PDF_TOOLS/pymupdf/extract-links.py" \
  "$TMPDIR_WORK/pymupdf.json" "$TMPDIR_WORK/links.jsonl" &
PID_LINKS=$!

# Image analysis on first-page PNG (skip if render failed)
PID_IMG_TOOLS=()
if [[ -n "$FIRST_PNG" ]]; then
  python3 "$IMAGE_TOOLS_CLI/extract-classify.py" "$FIRST_PNG" --output "$TMPDIR_WORK/img-classify.json" &
  PID_IMG_TOOLS+=("$!:img-classify")
  python3 "$IMAGE_TOOLS_CLI/extract-color.py"    "$FIRST_PNG" --output "$TMPDIR_WORK/img-color.json"    &
  PID_IMG_TOOLS+=("$!:img-color")
  python3 "$IMAGE_TOOLS_CLI/extract-meta.py"     "$FIRST_PNG" --output "$TMPDIR_WORK/img-meta.json"     &
  PID_IMG_TOOLS+=("$!:img-meta")
  python3 "$IMAGE_TOOLS_CLI/extract-quality.py"  "$FIRST_PNG" --output "$TMPDIR_WORK/img-quality.json"  &
  PID_IMG_TOOLS+=("$!:img-quality")
  python3 "$IMAGE_TOOLS_CLI/extract-text.py"     "$FIRST_PNG" --output "$TMPDIR_WORK/img-text.json"     &
  PID_IMG_TOOLS+=("$!:img-text")
  python3 "$IMAGE_TOOLS_CLI/extract-regions.py"  "$FIRST_PNG" --output "$TMPDIR_WORK/img-regions.json"  &
  PID_IMG_TOOLS+=("$!:img-regions")
fi

FAILED_B=0
for PID_NAME in \
  "$PID_MU_TXT:pymupdf-text" \
  "$PID_PM_TXT:pdfminer-text" \
  "$PID_PM_TBL:pdfminer-tables" \
  "$PID_LINKS:links" \
  "${PID_IMG_TOOLS[@]:-}"
do
  [[ -z "$PID_NAME" ]] && continue
  PID="${PID_NAME%%:*}"; NAME="${PID_NAME##*:}"
  if ! wait "$PID"; then
    echo "  Warning: $NAME failed" >&2
    FAILED_B=$((FAILED_B + 1))
  else
    echo "  Done: $NAME" >&2
  fi
done

[[ $FAILED_B -gt 0 ]] && echo "  ($FAILED_B phase-B tool(s) failed — continuing)" >&2

# ── phase C: vision prompts (sequential — one Ollama request at a time) ───────

if [[ -n "$FIRST_PNG" ]]; then
  echo "" >&2
  echo "Phase C — vision prompts (Ollama)..." >&2

  echo "  overview..." >&2
  python3 "$PROMPTS/extract-visible-overview-from-image.py" \
    "$FIRST_PNG" > "$TMPDIR_WORK/vision-overview.txt"

  echo "  layout..." >&2
  python3 "$PROMPTS/extract-visible-layout-from-image.py" \
    "$FIRST_PNG" > "$TMPDIR_WORK/vision-layout.txt"

  echo "  style..." >&2
  python3 "$PROMPTS/extract-visible-style-from-image.py" \
    "$FIRST_PNG" > "$TMPDIR_WORK/vision-style.txt"

  echo "  Done: all vision prompts" >&2
fi

# ── phase D: merge into final JSON ────────────────────────────────────────────

echo "" >&2
echo "Phase D — merging results..." >&2

python3 - "$PDF" "$IMAGES_DIR" "$TMPDIR_WORK" "$OUTPUT" <<'PYEOF'
import json
import sys
import datetime
import pathlib

pdf_path   = pathlib.Path(sys.argv[1])
images_dir = pathlib.Path(sys.argv[2])
tmp        = pathlib.Path(sys.argv[3])
output     = pathlib.Path(sys.argv[4])


def load_json(name):
    p = tmp / name
    if p.exists() and p.stat().st_size > 0:
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
    return None


def load_jsonl(name):
    p = tmp / name
    if not p.exists():
        return []
    records = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return records


def load_text(name):
    p = tmp / name
    return p.read_text(encoding="utf-8").strip() if p.exists() else ""


def load_images_manifest():
    m = images_dir / "manifest.json"
    if m.exists():
        try:
            return json.loads(m.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
    return None


# Page count from pymupdf artifact
pymupdf_data = load_json("pymupdf.json")
page_count = pymupdf_data.get("page_count") if pymupdf_data else None


def extract_header(pymupdf_artifact: dict | None) -> str | None:
    """Return the leading heading text from the raw pymupdf artifact.

    Determines body font size (mode weighted by char count), then returns
    the first line whose dominant size is >= 1.12x body (heading threshold).
    Falls back to the very first non-empty line if no headings are found.
    """
    if not pymupdf_artifact:
        return None

    from collections import Counter

    pages = pymupdf_artifact.get("pages", [])

    # Determine body font size across all pages
    sizes = []
    for page in pages:
        for block in page.get("blocks", []):
            if block.get("type") != "text":
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    t = span.get("text", "").strip()
                    if t:
                        sizes.extend([span.get("size", 0)] * max(1, len(t)))

    body_sz = Counter(round(s, 1) for s in sizes).most_common(1)[0][0] if sizes else 12.0

    first_line = None  # fallback if no heading found

    for page in pages:
        for block in page.get("blocks", []):
            if block.get("type") != "text":
                continue
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                line_text = "".join(s.get("text", "") for s in spans).strip()
                if not line_text:
                    continue
                if first_line is None:
                    first_line = line_text
                # Dominant font size for this line (by char count)
                sz_chars = [
                    (s.get("size", 0), len(s.get("text", "").strip()))
                    for s in spans if s.get("text", "").strip()
                ]
                if sz_chars:
                    dom_sz = max(sz_chars, key=lambda x: x[1])[0]
                    if body_sz > 0 and dom_sz / body_sz >= 1.12:
                        return line_text

    return first_line

# Canonical record count
canonical = load_jsonl("canonical.jsonl")

# First-page PNG exists?
png_paths = (tmp / "png-paths.txt")
has_png = png_paths.exists() and png_paths.stat().st_size > 0

vision = None
first_page_image = None
if has_png:
    vision = {
        "overview": load_text("vision-overview.txt"),
        "layout":   load_text("vision-layout.txt"),
        "style":    load_text("vision-style.txt"),
    }
    first_page_image = {
        "classification": load_json("img-classify.json"),
        "meta":           load_json("img-meta.json"),
        "quality":        load_json("img-quality.json"),
        "color":          load_json("img-color.json"),
        "text":           load_json("img-text.json"),
        "regions":        load_json("img-regions.json"),
        "vision":         vision,
    }

report = {
    "file":         pdf_path.name,
    "path":         str(pdf_path),
    "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
    "page_count":   page_count,
    "header":       extract_header(pymupdf_data),
    "text": {
        "pymupdf":  load_text("pymupdf-text.txt"),
        "pdfminer": load_text("pdfminer-text.txt"),
    },
    "tables": {
        "pymupdf":  load_json("pymupdf-tables.json"),
        "pdfminer": load_json("pdfminer-tables.json"),
    },
    "links":                load_jsonl("links.jsonl"),
    "images":               load_images_manifest(),
    "canonical_record_count": len(canonical),
    "first_page":           first_page_image,
}

output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Saved: {output}")
PYEOF

echo "" >&2
echo "Done." >&2
