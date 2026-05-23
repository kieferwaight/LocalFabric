"""Classify an image into one of 10 semantic types with a confidence score."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image

# ── Classification heuristics ─────────────────────────────────────────────────

_CLASSES = [
    "photograph",
    "screenshot",
    "diagram",
    "chart",
    "infographic",
    "illustration",
    "document",
    "blueprint",
    "logo",
    "other",
]


def classify_image(path: Path) -> dict:
    """
    Return a classification dict for the image at *path*.

    Schema::

        {
          "kind": str,          # primary class label
          "confidence": float,  # 0.0–1.0
          "scores": {label: float, ...}
        }
    """
    img_pil = Image.open(path).convert("RGB")
    img_np = np.array(img_pil)
    img_gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)

    w, h = img_pil.size
    aspect = w / h if h else 1.0

    # ── Signal extraction ─────────────────────────────────────────────────────

    # Edge density → high = diagram/blueprint/document, low = photograph
    edges = cv2.Canny(img_gray, 50, 150)
    edge_density = float(np.count_nonzero(edges)) / (w * h)

    # Unique colour count (sampled) → high = photograph, low = diagram/logo
    sample = img_pil.resize((100, 100), Image.Resampling.LANCZOS)
    unique_colors = len(set(sample.getdata()))

    # Saturation → high = infographic/illustration, low = document/blueprint
    img_hsv = cv2.cvtColor(img_np, cv2.COLOR_RGB2HSV)
    mean_sat = float(img_hsv[:, :, 1].mean()) / 255.0

    # Brightness variance → low = screenshot/document, high = photograph
    brightness = img_gray.astype(float)
    bright_var = float(brightness.var()) / (255.0**2)

    # ── Scoring ───────────────────────────────────────────────────────────────

    scores: dict[str, float] = {k: 0.0 for k in _CLASSES}

    # Photograph: many colours, low-medium edge density, natural aspect
    scores["photograph"] = (
        min(unique_colors / 5000, 1.0) * 0.5
        + (1.0 - min(edge_density * 10, 1.0)) * 0.3
        + bright_var * 0.2
    )

    # Screenshot: rectangular aspect near 16:9 or 4:3, many unique colours, low saturation
    is_screen_aspect = abs(aspect - 16 / 9) < 0.3 or abs(aspect - 4 / 3) < 0.2
    scores["screenshot"] = (
        (0.6 if is_screen_aspect else 0.1)
        + min(unique_colors / 3000, 1.0) * 0.3
        + (1.0 - mean_sat) * 0.1
    )

    # Diagram: high edge density, low colour variety, often wide aspect
    scores["diagram"] = (
        min(edge_density * 8, 1.0) * 0.5
        + (1.0 - min(unique_colors / 2000, 1.0)) * 0.3
        + (0.2 if aspect > 1.2 else 0.05)
    )

    # Chart: medium edges, low colour variety, wide aspect
    scores["chart"] = (
        min(edge_density * 5, 1.0) * 0.3
        + (1.0 - min(unique_colors / 1500, 1.0)) * 0.4
        + (0.3 if aspect > 1.3 else 0.05)
    )

    # Infographic: high saturation, tall or square aspect, medium edges
    scores["infographic"] = (
        mean_sat * 0.5
        + (0.3 if aspect < 0.9 else 0.05)
        + min(edge_density * 4, 1.0) * 0.2
    )

    # Illustration: high saturation, low edge density
    scores["illustration"] = mean_sat * 0.6 + (1.0 - min(edge_density * 8, 1.0)) * 0.4

    # Document: very low saturation, high edge density (text), tall or near-square
    scores["document"] = (
        (1.0 - mean_sat) * 0.4
        + min(edge_density * 6, 1.0) * 0.4
        + (0.2 if aspect < 1.1 else 0.05)
    )

    # Blueprint: very high edge density, low saturation, often dark bg
    mean_bright = float(img_gray.mean()) / 255.0
    scores["blueprint"] = (
        min(edge_density * 10, 1.0) * 0.5
        + (1.0 - mean_sat) * 0.3
        + (0.2 if mean_bright < 0.4 else 0.0)
    )

    # Logo: small unique colour count, high saturation, near-square
    scores["logo"] = (
        (1.0 - min(unique_colors / 500, 1.0)) * 0.4
        + mean_sat * 0.3
        + (0.3 if abs(aspect - 1.0) < 0.3 else 0.05)
    )

    scores["other"] = 0.05

    # Normalise
    total = sum(scores.values()) or 1.0
    scores = {k: round(v / total, 4) for k, v in scores.items()}

    kind = max(scores, key=lambda k: scores[k])
    confidence = round(scores[kind], 4)

    return {"kind": kind, "confidence": confidence, "scores": scores}
