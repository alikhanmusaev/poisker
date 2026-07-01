"""Generate PWA / Google Play icons (any + maskable safe zone)."""

import os

from PIL import Image, ImageDraw, ImageFont

ICONS_DIR = os.path.join(os.path.dirname(__file__), "app", "static", "icons")
DEMO_DIR = os.path.join(os.path.dirname(__file__), "app", "static", "demo")

DEMO_COLORS = {
    "default": "#b91c1c",
    "nedvizhimost": "#0284c7",
    "avto": "#4f46e5",
    "elektronika": "#7c3aed",
    "uslugi": "#0891b2",
    "zhivotnye": "#ca8a04",
    "prodazha": "#db2777",
    "dlya-doma": "#059669",
    "rabota": "#475569",
    "stroitelstvo": "#b45309",
    "detskie": "#ec4899",
    "zapchasti": "#64748b",
    "produkti": "#16a34a",
    "biznes": "#dc2626",
    "sport": "#2563eb",
    "rasteniya": "#65a30d",
    "drugoe": "#6b7280",
}


BRAND = "#b91c1c"


def _demo_image(slug: str, label: str) -> None:
    color = DEMO_COLORS.get(slug, DEMO_COLORS["default"])
    w, h = 640, 480
    img = Image.new("RGB", (w, h), color)
    draw = ImageDraw.Draw(img)
    draw.rectangle([24, 24, w - 24, h - 24], outline="#ffffff", width=3)
    font = _font(28)
    short = label[:18] + ("…" if len(label) > 18 else "")
    bbox = draw.textbbox((0, 0), short, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text(((w - tw) / 2, (h - th) / 2), short, fill="#ffffff", font=font)
    img.save(os.path.join(DEMO_DIR, f"{slug}.jpg"), "JPEG", quality=88)


def generate_demo_images():
    import sys

    sys.path.insert(0, os.path.dirname(__file__))
    from app.constants import CATEGORIES

    os.makedirs(DEMO_DIR, exist_ok=True)
    for slug, (label, _) in CATEGORIES.items():
        _demo_image(slug, label)
    _demo_image("default", "Объявление")
    print("Demo images generated")


def _font(size: int):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def _render(size: int, maskable: bool) -> Image.Image:
    img = Image.new("RGBA", (size, size), BRAND)
    draw = ImageDraw.Draw(img)

    if maskable:
        safe = int(size * 0.8)
        offset = (size - safe) // 2
        draw.rounded_rectangle(
            [offset, offset, offset + safe, offset + safe],
            radius=safe // 8,
            fill="#ffffff",
        )
    else:
        margin = size // 6
        draw.rounded_rectangle(
            [margin, margin, size - margin, size - margin],
            radius=size // 10,
            fill="#ffffff",
        )

    text = "П"
    font = _font(size // 4)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text(
        ((size - tw) / 2, (size - th) / 2 - size * 0.02),
        text,
        fill=BRAND,
        font=font,
    )
    return img


def generate():
    os.makedirs(ICONS_DIR, exist_ok=True)
    for size, maskable, name in (
        (192, False, "icon-192.png"),
        (512, False, "icon-512.png"),
        (192, True, "icon-maskable-192.png"),
        (512, True, "icon-maskable-512.png"),
    ):
        _render(size, maskable).save(os.path.join(ICONS_DIR, name), "PNG")
    print("Icons generated (any + maskable)")
    try:
        generate_demo_images()
    except Exception as e:
        print(f"Demo images skipped: {e}")


if __name__ == "__main__":
    generate()
