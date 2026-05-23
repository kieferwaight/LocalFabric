"""Full OCR text extraction with per-word bounding boxes and block groupings."""

from __future__ import annotations

from pathlib import Path

from PIL import Image


def extract_text(path: Path) -> dict:
    """
    Return OCR results for the image at *path*.

    Schema::

        {
          "full_text": str,
          "word_count": int,
          "words": [{"text": str, "conf": int, "x": int, "y": int, "w": int, "h": int}, ...],
          "blocks": [{"text": str, "x": int, "y": int, "w": int, "h": int}, ...]
        }
    """
    try:
        import pytesseract

        img = Image.open(path).convert("RGB")

        full_text: str = pytesseract.image_to_string(img).strip()

        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)

        words: list[dict] = []
        for i, text in enumerate(data["text"]):
            conf = int(data["conf"][i])
            if conf > 20 and text.strip():
                words.append(
                    {
                        "text": text.strip(),
                        "conf": conf,
                        "x": data["left"][i],
                        "y": data["top"][i],
                        "w": data["width"][i],
                        "h": data["height"][i],
                    }
                )

        # Group into paragraph-level blocks by block_num
        blocks: dict[int, dict] = {}
        for i, text in enumerate(data["text"]):
            conf = int(data["conf"][i])
            if conf <= 20 or not text.strip():
                continue
            bn = data["block_num"][i]
            if bn not in blocks:
                blocks[bn] = {
                    "text": "",
                    "x": data["left"][i],
                    "y": data["top"][i],
                    "w": data["width"][i],
                    "h": data["height"][i],
                }
            else:
                # Expand bbox
                bx = min(blocks[bn]["x"], data["left"][i])
                by = min(blocks[bn]["y"], data["top"][i])
                bx2 = max(blocks[bn]["x"] + blocks[bn]["w"], data["left"][i] + data["width"][i])
                by2 = max(blocks[bn]["y"] + blocks[bn]["h"], data["top"][i] + data["height"][i])
                blocks[bn]["x"] = bx
                blocks[bn]["y"] = by
                blocks[bn]["w"] = bx2 - bx
                blocks[bn]["h"] = by2 - by
            blocks[bn]["text"] = (blocks[bn]["text"] + " " + text.strip()).strip()

        return {
            "full_text": full_text,
            "word_count": len(words),
            "words": words,
            "blocks": list(blocks.values()),
        }

    except Exception as exc:
        return {
            "full_text": "",
            "word_count": 0,
            "words": [],
            "blocks": [],
            "error": str(exc),
        }
