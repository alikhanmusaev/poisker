"""Image privacy helpers — license plate blur on upload."""

from __future__ import annotations

import logging

from PIL import Image, ImageFilter

logger = logging.getLogger(__name__)

PLATE_BLUR_CATEGORIES = frozenset({"avto", "zapchasti"})


def blur_license_plates(img: Image.Image, *, category: str | None = None) -> Image.Image:
    """Best-effort blur of likely license plates in car-related photos."""
    if category not in PLATE_BLUR_CATEGORIES:
        return img

    try:
        import cv2
        import numpy as np
    except ImportError:
        logger.warning("opencv not installed; skipping license plate blur")
        return img

    rgb = np.array(img.convert("RGB"))
    height, width = rgb.shape[:2]
    if height < 120 or width < 120:
        return img

    roi_top = int(height * 0.35)
    roi = rgb[roi_top:, :]
    gray = cv2.cvtColor(roi, cv2.COLOR_RGB2GRAY)
    gray = cv2.bilateralFilter(gray, 11, 17, 17)
    edges = cv2.Canny(gray, 50, 180)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 3))
    edges = cv2.dilate(edges, kernel, iterations=1)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    mask = Image.new("L", img.size, 0)
    from PIL import ImageDraw

    draw = ImageDraw.Draw(mask)
    min_area = max(1800, int(width * height * 0.0015))
    found = False

    for contour in contours:
        x, y, cw, ch = cv2.boundingRect(contour)
        area = cw * ch
        if area < min_area or ch < max(12, height // 40) or cw < max(50, width // 12):
            continue
        aspect = cw / max(ch, 1)
        if not (1.8 <= aspect <= 7.5):
            continue
        pad_x = max(6, cw // 8)
        pad_y = max(4, ch // 4)
        x0 = max(0, x - pad_x)
        y0 = max(0, y + roi_top - pad_y)
        x1 = min(width, x + cw + pad_x)
        y1 = min(height, y + ch + roi_top + pad_y)
        draw.rectangle([x0, y0, x1, y1], fill=255)
        found = True

    if not found:
        return img

    blurred = img.filter(ImageFilter.GaussianBlur(radius=max(10, min(width, height) // 40)))
    return Image.composite(blurred, img, mask)
