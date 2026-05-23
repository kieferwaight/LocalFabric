#!/usr/bin/env python3
"""Archived legacy executable prompt wrapper for title generation."""

import subprocess
import json
import sys
import os
from pathlib import Path

def generate_title(text: str) -> str:
    """Call Ollama API to generate a title."""
    model = os.getenv("TITLE_MODEL", "mistral:7b-instruct")
    temperature = float(os.getenv("TITLE_TEMPERATURE", "0.7"))
    top_p = float(os.getenv("TITLE_TOP_P", "0.9"))
    num_predict = int(os.getenv("TITLE_NUM_PREDICT", "50"))
    api_url = os.getenv("OLLAMA_API", "http://localhost:11434/api/generate")

    prompt = f"""Generate the single best title for this text. Requirements:
- 5-10 words max
- Specific and descriptive
- Executive tone
- No fluff or filler words
- Punchy and clear

TEXT:
{text}

Return only the title, nothing else."""

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "top_p": top_p,
            "num_predict": num_predict
        }
    }

    # Call Ollama API via curl
    curl_cmd = [
        "curl", "-s", "-X", "POST", api_url,
        "-H", "Content-Type: application/json",
        "-d", json.dumps(payload)
    ]

    result = subprocess.run(curl_cmd, capture_output=True, text=True)

    try:
        response_json = json.loads(result.stdout)
        title = response_json.get("response", "").strip()
        return title
    except json.JSONDecodeError:
        print(f"Error: Could not parse API response: {result.stdout}", file=sys.stderr)
        sys.exit(1)

def main():
    # Get input
    if len(sys.argv) > 1 and Path(sys.argv[1]).is_file():
        with open(sys.argv[1], 'r') as f:
            text = f.read()
    elif not sys.stdin.isatty():
        text = sys.stdin.read()
    else:
        print("Usage: generate-title-from-text.py [file.txt]", file=sys.stderr)
        print("   or: cat file.txt | generate-title-from-text.py", file=sys.stderr)
        sys.exit(1)

    title = generate_title(text)
    print(title)

if __name__ == "__main__":
    main()
