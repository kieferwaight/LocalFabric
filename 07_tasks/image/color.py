"""Extract dominant colour palette, brightness, contrast, and saturation."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image


def extract_color(path: Path, n_colors: int = 6) -> dict:
    """
    Return colour analysis for the image at *path*.

    Schema::

        {
          "palette": [{"hex": str, "rgb": [r, g, b], "proportion": float}, ...],
          "brightness": float,    # 0.0–1.0 (mean luminance)
          "contrast": float,      # 0.0–1.0 (normalised std dev of luminance)
          "saturation": float,    # 0.0–1.0 (mean HSV saturation)
          "dominant_hex": str
        }
    """
    img_pil = Image.open(path).convert("RGB")

    # ── Palette via k-means ───────────────────────────────────────────────────
    small = img_pil.resize((150, 150), Image.Resampling.LANCZOS)
    pixels = np.array(small, dtype=np.float32).reshape(-1, 3)
    best_labels = np.zeros((pixels.shape[0], 1), dtype=np.int32)

    _, labels, centers = cv2.kmeans(
        pixels,
        n_colors,
        best_labels,
        (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 0.5),
        5,
        cv2.KMEANS_RANDOM_CENTERS,
    )

    counts = np.bincount(labels.flatten(), minlength=n_colors)
    total = counts.sum() or 1
    palette = []
    for i in np.argsort(-counts):  # most common first
        r, g, b = (int(c) for c in centers[i])
        palette.append(
            {
                "hex": f"#{r:02x}{g:02x}{b:02x}",
                "rgb": [r, g, b],
                "proportion": round(float(counts[i]) / total, 4),
            }
        )

    # ── Brightness & contrast ─────────────────────────────────────────────────
    img_np = np.array(img_pil)
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY).astype(float)
    brightness = round(float(gray.mean()) / 255.0, 4)
    contrast = round(float(gray.std()) / 255.0, 4)

    # ── Saturation ────────────────────────────────────────────────────────────
    hsv = cv2.cvtColor(img_np, cv2.COLOR_RGB2HSV)
    saturation = round(float(hsv[:, :, 1].mean()) / 255.0, 4)

    return {
        "palette": palette,
        "dominant_hex": palette[0]["hex"] if palette else "#000000",
        "brightness": brightness,
        "contrast": contrast,
        "saturation": saturation,
    }
