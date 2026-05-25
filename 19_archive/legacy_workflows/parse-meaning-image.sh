#!/usr/bin/env bash
# Archived legacy shell workflow for parsing the meaning of an image file.
#
# Runs all image extraction tools to gather structured signals, then calls
# the three Ollama vision prompts for overview, layout, and style. Merges
# everything into a single JSON report saved next to the input image.
#
# Usage:
#   bash 06_workflows/shell/parse-meaning-image.sh [image]
#
# NOTE: This script expects CLI wrappers for the image extraction tools
# under 07_tools/image/cli/ (one .py per signal, accepting <image> [--output]).
# Those wrappers were not part of the ai_utils migration — the Python
# functions live in 07_tools/image/{classify,color,meta,quality,regions,text_ocr}.py
# and are invoked via the LangGraph workflow (see 06_workflows/langgraph/image_intelligence/).
# This shell variant is preserved as a historical reference.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACES_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# ── tool / prompt locations under the new bucket layout ──────────────────────

IMAGE_TOOLS_CLI="$WORKSPACES_ROOT/07_tools/image/cli"
PROMPTS_DIR="$WORKSPACES_ROOT/12_prompts/tasks"

# ── input & output paths ──────────────────────────────────────────────────────

IMAGE="${1:-}"
if [[ -z "$IMAGE" ]]; then
  echo "Usage: $0 <image>" >&2
  exit 1
fi
IMAGE="$(python3 -c "import pathlib, sys; print(pathlib.Path(sys.argv[1]).resolve())" "$IMAGE")"

if [[ ! -f "$IMAGE" ]]; then
  echo "Error: file not found: $IMAGE" >&2
  exit 1
fi

OUTPUT="${IMAGE%.*}.json"

echo "Image:  $IMAGE" >&2
echo "Output: $OUTPUT" >&2

# ── temp workspace ────────────────────────────────────────────────────────────

TMPDIR_WORK="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_WORK"' EXIT

# ── run extraction tools in parallel ─────────────────────────────────────────

echo "" >&2
echo "Running extraction tools..." >&2

python3 "$IMAGE_TOOLS_CLI/extract-classify.py" \
  "$IMAGE" --output "$TMPDIR_WORK/classify.json" &
PID_CLASSIFY=$!

python3 "$IMAGE_TOOLS_CLI/extract-color.py" \
  "$IMAGE" --output "$TMPDIR_WORK/color.json" &
PID_COLOR=$!

python3 "$IMAGE_TOOLS_CLI/extract-meta.py" \
  "$IMAGE" --output "$TMPDIR_WORK/meta.json" &
PID_META=$!

python3 "$IMAGE_TOOLS_CLI/extract-quality.py" \
  "$IMAGE" --output "$TMPDIR_WORK/quality.json" &
PID_QUALITY=$!

python3 "$IMAGE_TOOLS_CLI/extract-text.py" \
  "$IMAGE" --output "$TMPDIR_WORK/text.json" &
PID_TEXT=$!

python3 "$IMAGE_TOOLS_CLI/extract-regions.py" \
  "$IMAGE" --output "$TMPDIR_WORK/regions.json" &
PID_REGIONS=$!

# Wait for all and collect exit codes
FAILED=0
for PID_NAME in \
  "$PID_CLASSIFY:classify" \
  "$PID_COLOR:color" \
  "$PID_META:meta" \
  "$PID_QUALITY:quality" \
  "$PID_TEXT:text" \
  "$PID_REGIONS:regions"
do
  PID="${PID_NAME%%:*}"
  NAME="${PID_NAME##*:}"
  if ! wait "$PID"; then
    echo "  Warning: $NAME extractor failed" >&2
    FAILED=$((FAILED + 1))
  else
    echo "  Done: $NAME" >&2
  fi
done

if [[ $FAILED -gt 0 ]]; then
  echo "Warning: $FAILED extractor(s) failed — continuing with partial data" >&2
fi

# ── run vision prompts sequentially ──────────────────────────────────────────

echo "" >&2
echo "Running vision prompts (Ollama)..." >&2

echo "  overview..." >&2
python3 "$PROMPTS_DIR/extract-visible-overview-from-image.py" \
  "$IMAGE" > "$TMPDIR_WORK/overview.txt"

echo "  layout..." >&2
python3 "$PROMPTS_DIR/extract-visible-layout-from-image.py" \
  "$IMAGE" > "$TMPDIR_WORK/layout.txt"

echo "  style..." >&2
python3 "$PROMPTS_DIR/extract-visible-style-from-image.py" \
  "$IMAGE" > "$TMPDIR_WORK/style.txt"

echo "  Done: all vision prompts" >&2

# ── merge into final JSON ─────────────────────────────────────────────────────

echo "" >&2
echo "Merging results..." >&2

python3 - "$IMAGE" "$TMPDIR_WORK" "$OUTPUT" <<'PYEOF'
import json
import sys
import datetime
import pathlib

image_path = pathlib.Path(sys.argv[1])
tmp        = pathlib.Path(sys.argv[2])
output     = pathlib.Path(sys.argv[3])


def load_json(name):
    p = tmp / name
    if p.exists() and p.stat().st_size > 0:
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
    return None


def load_text(name):
    p = tmp / name
    if p.exists():
        return p.read_text(encoding="utf-8").strip()
    return ""


report = {
    "file":         image_path.name,
    "path":         str(image_path),
    "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
    "classification": load_json("classify.json"),
    "meta":           load_json("meta.json"),
    "quality":        load_json("quality.json"),
    "color":          load_json("color.json"),
    "text":           load_json("text.json"),
    "regions":        load_json("regions.json"),
    "vision": {
        "overview": load_text("overview.txt"),
        "layout":   load_text("layout.txt"),
        "style":    load_text("style.txt"),
    },
}

output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Saved: {output}")
PYEOF

echo "" >&2
echo "Done." >&2
