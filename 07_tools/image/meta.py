"""Extract file identity metadata, dimensions, EXIF, and ICC profile info."""

from __future__ import annotations

import hashlib
import mimetypes
from pathlib import Path

from PIL import ExifTags, Image
from PIL.Image import Exif


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _parse_exif(exif: Exif | None) -> dict:
    if not exif:
        return {}
    result: dict[str, object] = {}
    for tag_id, value in exif.items():
        tag = ExifTags.TAGS.get(tag_id, str(tag_id))
        # Skip binary blobs
        if isinstance(value, bytes) and len(value) > 64:
            continue
        try:
            result[tag] = str(value)
        except Exception:
            pass
    return result


def extract_meta(path: Path) -> dict:
    """
    Return file identity metadata for the image at *path*.

    Schema::

        {
          "sha256": str,
          "size_bytes": int,
          "filename": str,
          "extension": str,
          "mime_type": str | None,
          "width": int,
          "height": int,
          "mode": str,           # e.g. "RGB", "RGBA", "L"
          "format": str | None,  # e.g. "JPEG", "PNG"
          "has_exif": bool,
          "exif": dict,
          "has_icc": bool,
          "icc_description": str | None
        }
    """
    stat = path.stat()
    sha = _sha256(path)
    mime, _ = mimetypes.guess_type(str(path))

    img = Image.open(path)
    w, h = img.size

    exif_data = img.getexif() if hasattr(img, "getexif") else None
    exif_dict = _parse_exif(exif_data)

    icc = img.info.get("icc_profile")
    icc_desc: str | None = None
    if icc:
        # Try to pull a human-readable description from the raw ICC blob
        try:
            import io

            import PIL.ImageCms as cms

            profile = cms.ImageCmsProfile(io.BytesIO(icc))
            icc_desc = cms.getProfileDescription(profile)
        except Exception:
            icc_desc = "present"

    return {
        "sha256": sha,
        "size_bytes": stat.st_size,
        "filename": path.name,
        "extension": path.suffix.lstrip(".").lower(),
        "mime_type": mime,
        "width": w,
        "height": h,
        "mode": img.mode,
        "format": img.format,
        "has_exif": bool(exif_dict),
        "exif": exif_dict,
        "has_icc": bool(icc),
        "icc_description": icc_desc,
    }
