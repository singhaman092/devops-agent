"""RapidOCR wrapper — find text in images."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def find_text_in_image(
    image_path: str | Path,
    target_text: str,
) -> dict[str, Any] | None:
    """Find target_text in an image using RapidOCR.

    Returns dict with center_x, center_y, confidence, bbox if found, else None.
    """
    from rapidocr_onnxruntime import RapidOCR  # type: ignore[import-untyped]

    ocr = RapidOCR()
    result, _ = ocr(str(image_path))

    if result is None:
        return None

    for item in result:
        boxes, detected_text, confidence = item
        if target_text.lower() in detected_text.lower():
            xs = [p[0] for p in boxes]
            ys = [p[1] for p in boxes]
            return {
                "found": True,
                "text": detected_text,
                "center_x": sum(xs) / len(xs),
                "center_y": sum(ys) / len(ys),
                "confidence": confidence,
                "bbox": boxes,
            }

    return None
