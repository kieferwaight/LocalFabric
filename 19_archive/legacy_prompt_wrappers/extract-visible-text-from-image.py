#!/usr/bin/env python3
"""Archived legacy executable prompt wrapper for visible text extraction."""

import base64
import json
import sys
import os
import urllib.request
import urllib.error
from pathlib import Path

def extract_text(image_path: str) -> str:
    """Extract visible text from image."""
    model = os.getenv("VISION_MODEL", "llama3.2-vision")
    temperature = float(os.getenv("VISION_TEXT_TEMPERATURE", "0.0"))
    top_p = float(os.getenv("VISION_TEXT_TOP_P", "0.8"))
    top_k = int(os.getenv("VISION_TEXT_TOP_K", "20"))
    repeat_penalty = float(os.getenv("VISION_TEXT_REPEAT_PENALTY", "1.35"))
    repeat_last_n = int(os.getenv("VISION_TEXT_REPEAT_LAST_N", "256"))
    num_predict = int(os.getenv("VISION_TEXT_NUM_PREDICT", "120"))
    api_url = os.getenv("OLLAMA_API") or "http://localhost:11434/api/generate"

    # Read and encode image
    with open(image_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")

    prompt = """Extract only the exact visible text from the image.
Return exactly this markdown shape:
## Text
- <exact visible text line 1>
- <exact visible text line 2>
- <exact visible text line 3>
Rules:
- Maximum 8 bullets.
- Preserve exact wording and line breaks as much as possible.
- Do not summarize.
- Do not explain the text.
- Do not repeat any extracted line.
- Do not mention missing or unreadable text unless nothing at all is readable; then return one bullet: "No readable text."
- No placeholders except the angle-bracket examples in this template.
- End with <END>."""

    payload = {
        "model": model,
        "prompt": prompt,
        "images": [image_data],
        "stream": False,
        "options": {
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
            "repeat_penalty": repeat_penalty,
            "repeat_last_n": repeat_last_n,
            "num_predict": num_predict,
            "stop": ["<END>", "\n## END", "\n--- END"]
        }
    }

    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        api_url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as resp:
            response_json = json.loads(resp.read().decode("utf-8"))
            return response_json.get("response", "").strip()
    except urllib.error.URLError as e:
        print(f"Error: Could not reach Ollama at {api_url}: {e.reason}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Could not parse API response: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    if len(sys.argv) > 1 and Path(sys.argv[1]).is_file():
        image_path = sys.argv[1]
    else:
        print("Usage: extract-visible-text-from-image.py image.png", file=sys.stderr)
        sys.exit(1)

    output = extract_text(image_path)
    print(output)

if __name__ == "__main__":
    main()
