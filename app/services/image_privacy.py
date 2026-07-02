"""Image privacy helpers — license plate blur on upload."""

from __future__ import annotations

import logging

from PIL import Image, ImageDraw, ImageFilter

logger = logging.getLogger(__name__)

PLATE_BLUR_CATEGORIES = frozenset({"avto", "zapchasti"})
_PLATE_ASPECT_MIN = 2.2
_PLATE_ASPECT_MAX = 6.0
_PLATE_ASPECT_IDEAL = 3.8
_MAX_BLUR_REGIONS = 1
_MIN_SCORE = 0.55
_MIN_TEXTURE = 0.32
_EARLY_EXIT_SCORE = 0.72


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
    limits = _plate_size_limits(width, height)

    candidates: list[tuple[float, tuple[int, int, int, int]]] = []
    for box in _contour_candidates(rgb, int(height * 0.52), 0, width, limits):
        candidates.append(_evaluate_candidate(box, width, height, rgb))

    coarse = _scan_plate_window(rgb, limits, coarse=True)
    if coarse[1]:
        candidates.append(coarse)

    best_score = max((score for score, box in candidates if box), default=0.0)
    if best_score < 0.6:
        fine = _scan_plate_window(rgb, limits, coarse=False)
        if fine[1]:
            candidates.append(fine)

    candidates = [(score, box) for score, box in candidates if box and score >= _MIN_SCORE]
    if not candidates:
        return []

    candidates.sort(key=lambda item: item[0], reverse=True)
    return [candidates[0][1]]


def _evaluate_candidate(
    box: tuple[int, int, int, int],
    width: int,
    height: int,
    rgb,
) -> tuple[float, tuple[int, int, int, int] | None]:
    if not _has_car_context(rgb, box):
        return 0.0, None
    texture = _plate_texture_score(rgb, box)
    if texture < _MIN_TEXTURE:
        return 0.0, None
    return _score_plate_box(box, width, height, rgb, texture=texture), box


def _has_car_context(rgb, box: tuple[int, int, int, int]) -> bool:
    """Plates are mounted on the bumper, not on dark asphalt below the car."""
    x0, y0, x1, y1 = box
    if y0 < 10:
        return True
    above = rgb[max(0, y0 - 12):y0, x0:x1]
    if above.size == 0:
        return True
    return float(above.mean()) >= 105


def _scan_plate_window(rgb, limits: dict[str, int], *, coarse: bool) -> tuple[float, tuple[int, int, int, int] | None]:
    height, width = rgb.shape[:2]
    roi_y0 = int(height * 0.58)
    bh_step = 6 if coarse else 3
    bw_step = 14 if coarse else 8
    pos_step = 22 if coarse else 12

    best_score = 0.0
    best_box = None

    for bh in range(limits["min_h"], limits["max_h"] + 1, bh_step):
        for bw in range(limits["min_w"], limits["max_w"] + 1, bw_step):
            aspect = bw / bh
            if not (_PLATE_ASPECT_MIN <= aspect <= _PLATE_ASPECT_MAX):
                continue
            for y0 in range(roi_y0, height - bh + 1, pos_step):
                for x0 in range(0, width - bw + 1, pos_step):
                    box = (x0, y0, x0 + bw, y0 + bh)
                    score, candidate = _evaluate_candidate(box, width, height, rgb)
                    if candidate and score > best_score:
                        best_score = score
                        best_box = candidate
                        if best_score >= _EARLY_EXIT_SCORE:
                            return best_score, best_box

    return best_score, best_box


def _plate_size_limits(width: int, height: int) -> dict[str, int]:
    return {
        "min_w": max(40, int(width * 0.05)),
        "max_w": int(width * 0.24),
        "min_h": max(8, int(height * 0.012)),
        "max_h": int(height * 0.08),
        "max_area": int(width * height * 0.03),
    }


def _contour_candidates(
    rgb,
    roi_y0: int,
    roi_x0: int,
    roi_x1: int,
    limits: dict[str, int],
) -> list[tuple[int, int, int, int]]:
    import cv2

    height, width = rgb.shape[:2]
    roi = rgb[roi_y0:height, roi_x0:roi_x1]
    hsv = cv2.cvtColor(roi, cv2.COLOR_RGB2HSV)
    white_mask = cv2.inRange(hsv, (0, 0, 158), (180, 75, 255))
    yellow_mask = cv2.inRange(hsv, (10, 55, 130), (45, 255, 255))
    binary = cv2.bitwise_or(white_mask, yellow_mask)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 3))
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=1)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)))

    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes: list[tuple[int, int, int, int]] = []

    for contour in contours:
        box = _box_from_contour(contour, roi_y0, roi_x0, width, height, limits)
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
    if area > limits["max_area"] or area < limits["min_w"] * limits["min_h"] * 0.35:
        return None
    if cw < limits["min_w"] or cw > limits["max_w"]:
        return None
    if ch < limits["min_h"] or ch > limits["max_h"]:
        return None

    aspect = cw / max(ch, 1)
    if not (_PLATE_ASPECT_MIN <= aspect <= _PLATE_ASPECT_MAX):
        return None

    contour_area = cv2.contourArea(contour)
    if contour_area <= 0 or contour_area / area < 0.25:
        return None

    pad_x = max(3, cw // 12)
    pad_y = max(2, ch // 8)
    x0 = max(0, x + roi_x0 - pad_x)
    y0 = max(0, y + roi_y0 - pad_y)
    x1 = min(width, x + cw + roi_x0 + pad_x)
    y1 = min(height, y + ch + roi_y0 + pad_y)

    if (x1 - x0) > limits["max_w"] + pad_x * 2:
        return None
    if (y1 - y0) > limits["max_h"] + pad_y * 2:
        return None
    return x0, y0, x1, y1


def _plate_texture_score(rgb, box: tuple[int, int, int, int]) -> float:
    """Detect dark glyphs on a bright plate background."""
    import cv2
    import numpy as np

    x0, y0, x1, y1 = box
    patch = rgb[y0:y1, x0:x1]
    if patch.size == 0:
        return 0.0

    gray = cv2.cvtColor(patch, cv2.COLOR_RGB2GRAY)
    mean = float(gray.mean())
    if mean < 118 or mean > 248:
        return 0.0

    hsv = cv2.cvtColor(patch, cv2.COLOR_RGB2HSV)
    plate_color_ratio = float(((hsv[:, :, 2] > 138) & (hsv[:, :, 1] < 95)).mean())
    if plate_color_ratio < 0.72:
        return 0.0

    dark_ratio = float((gray < 95).mean())
    if dark_ratio < 0.035 or dark_ratio > 0.42:
        return 0.0

    char_peaks = _count_dark_peaks(gray)
    if char_peaks < 2 or char_peaks > 5:
        return 0.0

    edges = cv2.Canny(gray, 45, 130)
    edge_density = float(edges.mean()) / 255.0
    if edge_density < 0.045:
        return 0.0

    row_signal = edges.mean(axis=1) / 255.0
    col_signal = edges.mean(axis=0) / 255.0
    if row_signal.max() < 0.12:
        return 0.0
    if col_signal.std() < 0.025:
        return 0.0

    peak_score = min(1.0, char_peaks / 7.0)
    return min(
        1.0,
        plate_color_ratio * 0.35
        + peak_score * 0.35
        + edge_density * 1.5
        + dark_ratio * 1.2,
    )


def _count_dark_peaks(gray) -> int:
    import numpy as np

    projection = (gray < 95).sum(axis=0)
    if projection.size < 8:
        return 0
    smoothed = np.convolve(projection.astype(float), np.ones(3) / 3, mode="same")
    peaks = 0
    for idx in range(1, len(smoothed) - 1):
        if smoothed[idx] > smoothed[idx - 1] and smoothed[idx] > smoothed[idx + 1]:
            if smoothed[idx] >= max(2.0, smoothed.max() * 0.25):
                peaks += 1
    return peaks


def _score_plate_box(
    box: tuple[int, int, int, int],
    width: int,
    height: int,
    rgb,
    *,
    texture: float,
) -> float:
    x0, y0, x1, y1 = box
    bw = x1 - x0
    bh = y1 - y0
    if bw <= 0 or bh <= 0:
        return 0.0

    aspect = bw / bh
    if not (_PLATE_ASPECT_MIN <= aspect <= _PLATE_ASPECT_MAX):
        return 0.0

    area_ratio = (bw * bh) / (width * height)
    if area_ratio > 0.04 or area_ratio < 0.0007:
        return 0.0

    aspect_score = 1.0 - min(abs(aspect - _PLATE_ASPECT_IDEAL) / _PLATE_ASPECT_IDEAL, 1.0)
    cy = (y0 + y1) / 2 / height
    # Russian front/rear plates sit on the bumper — near the bottom edge.
    if cy < 0.83:
        return 0.0
    position_score = min(1.0, (cy - 0.83) / 0.07)

    cx = (x0 + x1) / 2 / width
    # Plates are rarely glued to the far image edge (often pavement glints there).
    edge_penalty = 0.0
    if cx > 0.88 or cx < 0.02:
        edge_penalty = 0.35
    elif cx > 0.82 or cx < 0.05:
        edge_penalty = 0.15

    # On angled car photos the visible plate is on a lower bumper corner, not under the doors.
    side_distance = min(abs(cx - 0.2), abs(cx - 0.8))
    side_score = max(0.0, 1.0 - side_distance / 0.28)

    return max(
        0.0,
        texture * 0.45
        + aspect_score * 0.2
        + position_score * 0.15
        + side_score * 0.2
        - edge_penalty,
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
