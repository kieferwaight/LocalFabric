"""Assess image quality: blur score, edge density, near-blank detection."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image


def extract_quality(path: Path) -> dict:
    """
    Return quality metrics for the image at *path*.

    Schema::

        {
          "blur_score": float,      # higher = sharper (Laplacian variance)
          "is_blurry": bool,        # blur_score < threshold
          "edge_density": float,    # 0.0–1.0 fraction of edge pixels
          "is_blank": bool,         # near-uniform image
          "mean_brightness": float, # 0.0–1.0
          "brightness_std": float,  # 0.0–1.0
        }
    """
    img_pil = Image.open(path).convert("RGB")
    img_np = np.array(img_pil)
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)

    # ── Blur (Laplacian variance) ─────────────────────────────────────────────
    lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    is_blurry = lap_var < 100.0  # empirical threshold

    # ── Edge density ──────────────────────────────────────────────────────────
    edges = cv2.Canny(gray, 50, 150)
    h, w = gray.shape
    edge_density = round(float(np.count_nonzero(edges)) / (w * h), 6)

    # ── Near-blank detection ──────────────────────────────────────────────────
    mean_bright = float(gray.mean()) / 255.0
    bright_std = float(gray.std()) / 255.0
    is_blank = bright_std < 0.03  # very little variation → blank / solid colour

    return {
        "blur_score": round(lap_var, 2),
        "is_blurry": is_blurry,
        "edge_density": edge_density,
        "is_blank": is_blank,
        "mean_brightness": round(mean_bright, 4),
        "brightness_std": round(bright_std, 4),
    }
