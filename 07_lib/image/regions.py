"""Detect visible content regions, OCR text bounding boxes, and graphic contours."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image


def _bbox_to_dict(x: int, y: int, w: int, h: int) -> dict:
    return {"x": x, "y": y, "w": w, "h": h}


def extract_regions(path: Path, max_contours: int = 20) -> dict:
    """
    Return visible region data for the image at *path*.

    Schema::

        {
          "content_bbox": {"x", "y", "w", "h"},  # bounding box of non-white content
          "ocr_regions": [{"x", "y", "w", "h"}, ...],  # Tesseract block bboxes
          "contours": [{"x", "y", "w", "h", "area": float}, ...],  # top graphic contours
          "image_width": int,
          "image_height": int
        }
    """
    img_pil = Image.open(path).convert("RGB")
    img_np = np.array(img_pil)
    h_img, w_img = img_np.shape[:2]

    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)

    # ── Content bounding box (non-white region) ───────────────────────────────
    _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
    coords = cv2.findNonZero(thresh)
    if coords is not None:
        rx, ry, rw, rh = cv2.boundingRect(coords)
        content_bbox = _bbox_to_dict(rx, ry, rw, rh)
    else:
        content_bbox = _bbox_to_dict(0, 0, w_img, h_img)

    # ── OCR regions via Tesseract ─────────────────────────────────────────────
    ocr_regions: list[dict] = []
    try:
        import pytesseract

        data = pytesseract.image_to_data(img_pil, output_type=pytesseract.Output.DICT)
        for i, text in enumerate(data["text"]):
            conf = int(data["conf"][i])
            if conf > 30 and text.strip():
                ocr_regions.append(
                    _bbox_to_dict(
                        data["left"][i],
                        data["top"][i],
                        data["width"][i],
                        data["height"][i],
                    )
                )
    except Exception:
        pass  # Tesseract not available — skip gracefully

    # ── Graphic contours ──────────────────────────────────────────────────────
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 30, 100)
    cnts, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    contour_dicts: list[dict] = []
    min_area = (w_img * h_img) * 0.001  # ignore tiny noise contours
    for c in sorted(cnts, key=cv2.contourArea, reverse=True)[:max_contours]:
        area = cv2.contourArea(c)
        if area < min_area:
            break
        cx, cy, cw, ch = cv2.boundingRect(c)
        contour_dicts.append(
            {**_bbox_to_dict(cx, cy, cw, ch), "area": round(float(area), 1)}
        )

    return {
        "content_bbox": content_bbox,
        "ocr_regions": ocr_regions,
        "contours": contour_dicts,
        "image_width": w_img,
        "image_height": h_img,
    }
