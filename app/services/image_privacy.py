"""Image privacy helpers — license plate blur on upload."""

from __future__ import annotations

import logging

from PIL import Image, ImageDraw, ImageFilter

logger = logging.getLogger(__name__)

PLATE_BLUR_CATEGORIES = frozenset({"avto", "zapchasti"})
_PLATE_ASPECT_MIN = 2.2
_PLATE_ASPECT_MAX = 5.8
_PLATE_ASPECT_IDEAL = 3.8
_MAX_BLUR_REGIONS = 2


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
    if height < 160 or width < 160:
        return img

    boxes = _find_plate_boxes(rgb)
    if not boxes:
        return img

    mask = Image.new("L", img.size, 0)
    draw = ImageDraw.Draw(mask)
    blur_radius = max(8, min(width, height) // 80)

    for x0, y0, x1, y1 in boxes[:_MAX_BLUR_REGIONS]:
        draw.rectangle([x0, y0, x1, y1], fill=255)

    blurred = img.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    return Image.composite(blurred, img, mask)


def _find_plate_boxes(rgb) -> list[tuple[int, int, int, int]]:
    height, width = rgb.shape[:2]
    roi_y0 = int(height * 0.45)
    roi_x0 = int(width * 0.05)
    roi_x1 = int(width * 0.95)

    limits = _plate_size_limits(width, height)
    candidates: list[tuple[float, tuple[int, int, int, int]]] = []

    for mode in ("bright", "edge"):
        for box in _contour_candidates(rgb, roi_y0, roi_x0, roi_x1, limits, mode=mode):
            score = _score_plate_box(box, width, height, rgb)
            if score >= 0.45:
                candidates.append((score, box))

    if not candidates:
        return []

    candidates.sort(key=lambda item: item[0], reverse=True)
    selected: list[tuple[int, int, int, int]] = []
    for _score, box in candidates:
        if any(_boxes_overlap(box, kept, threshold=0.3) for kept in selected):
            continue
        selected.append(box)
        if len(selected) >= _MAX_BLUR_REGIONS:
            break
    return selected


def _plate_size_limits(width: int, height: int) -> dict[str, int]:
    return {
        "min_w": max(42, int(width * 0.055)),
        "max_w": int(width * 0.22),
        "min_h": max(8, int(height * 0.014)),
        "max_h": int(height * 0.075),
        "max_area": int(width * height * 0.028),
    }


def _contour_candidates(
    rgb,
    roi_y0: int,
    roi_x0: int,
    roi_x1: int,
    limits: dict[str, int],
    *,
    mode: str,
) -> list[tuple[int, int, int, int]]:
    import cv2

    height, width = rgb.shape[:2]
    roi = rgb[roi_y0:height, roi_x0:roi_x1]
    gray = cv2.cvtColor(roi, cv2.COLOR_RGB2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)

    if mode == "bright":
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        if gray.mean() > 110:
            binary = cv2.bitwise_not(binary)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 3))
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=1)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)))
    else:
        edges = cv2.Canny(gray, 100, 220)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        binary = cv2.dilate(edges, kernel, iterations=1)

    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes: list[tuple[int, int, int, int]] = []

    for contour in contours:
        box = _box_from_contour(
            contour,
            roi_y0,
            roi_x0,
            width,
            height,
            limits,
        )
        if box:
            boxes.append(box)

    return boxes


def _box_from_contour(
    contour,
    roi_y0: int,
    roi_x0: int,
    width: int,
    height: int,
    limits: dict[str, int],
) -> tuple[int, int, int, int] | None:
    import cv2

    x, y, cw, ch = cv2.boundingRect(contour)
    area = cw * ch
    if area > limits["max_area"] or area < limits["min_w"] * limits["min_h"] * 0.4:
        return None
    if cw < limits["min_w"] or cw > limits["max_w"]:
        return None
    if ch < limits["min_h"] or ch > limits["max_h"]:
        return None

    aspect = cw / max(ch, 1)
    if not (_PLATE_ASPECT_MIN <= aspect <= _PLATE_ASPECT_MAX):
        return None

    contour_area = cv2.contourArea(contour)
    if contour_area <= 0 or contour_area / area < 0.2:
        return None

    pad_x = max(2, cw // 14)
    pad_y = max(2, ch // 10)
    x0 = max(0, x + roi_x0 - pad_x)
    y0 = max(0, y + roi_y0 - pad_y)
    x1 = min(width, x + cw + roi_x0 + pad_x)
    y1 = min(height, y + ch + roi_y0 + pad_y)

    if (x1 - x0) > limits["max_w"] + pad_x * 2:
        return None
    if (y1 - y0) > limits["max_h"] + pad_y * 2:
        return None
    return x0, y0, x1, y1


def _score_plate_box(box: tuple[int, int, int, int], width: int, height: int, rgb) -> float:
    x0, y0, x1, y1 = box
    bw = x1 - x0
    bh = y1 - y0
    if bw <= 0 or bh <= 0:
        return 0.0

    aspect = bw / bh
    if not (_PLATE_ASPECT_MIN <= aspect <= _PLATE_ASPECT_MAX):
        return 0.0

    area_ratio = (bw * bh) / (width * height)
    if area_ratio > 0.035 or area_ratio < 0.0008:
        return 0.0

    aspect_score = 1.0 - min(abs(aspect - _PLATE_ASPECT_IDEAL) / _PLATE_ASPECT_IDEAL, 1.0)
    cy = (y0 + y1) / 2 / height
    position_score = 1.0 if cy >= 0.62 else max(0.0, (cy - 0.45) / 0.17)

    patch = rgb[y0:y1, x0:x1]
    if patch.size == 0:
        return 0.0
    luminance = float(patch.mean())
    brightness_score = min(max((luminance - 100) / 100, 0.0), 1.0)

    cx = (x0 + x1) / 2 / width
    center_score = 1.0 - min(abs(cx - 0.5) / 0.4, 1.0)

    size_score = 1.0 - min(max((area_ratio - 0.012) / 0.02, 0.0), 1.0)

    return (
        aspect_score * 0.3
        + position_score * 0.28
        + brightness_score * 0.22
        + center_score * 0.1
        + size_score * 0.1
    )


def _boxes_overlap(
    a: tuple[int, int, int, int],
    b: tuple[int, int, int, int],
    *,
    threshold: float,
) -> bool:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0 = max(ax0, bx0)
    iy0 = max(ay0, by0)
    ix1 = min(ax1, bx1)
    iy1 = min(ay1, by1)
    if ix1 <= ix0 or iy1 <= iy0:
        return False
    inter = (ix1 - ix0) * (iy1 - iy0)
    area_a = (ax1 - ax0) * (ay1 - ay0)
    area_b = (bx1 - bx0) * (by1 - by0)
    return inter / min(area_a, area_b) >= threshold
