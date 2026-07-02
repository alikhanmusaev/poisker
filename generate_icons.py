"""Generate PWA / Google Play icons from brand assets."""

import os

from PIL import Image, ImageDraw, ImageFont

ICONS_DIR = os.path.join(os.path.dirname(__file__), "app", "static", "icons")
BRAND_DIR = os.path.join(os.path.dirname(__file__), "app", "static", "brand")
BRAND_ICON_SOURCE = os.path.join(BRAND_DIR, "icon-source.png")
BRAND_LOGO_SOURCE = os.path.join(BRAND_DIR, "logo-source.png")
BRAND_ICON = os.path.join(BRAND_DIR, "icon.png")
BRAND_LOGO = os.path.join(BRAND_DIR, "logo.png")
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
BRAND_RGB = (185, 28, 28)


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


def _is_dark_pixel(r: int, g: int, b: int, a: int) -> bool:
    if a < 20:
        return False
    return max(r, g, b) < 64


def tint_logo_to_brand(image: Image.Image) -> Image.Image:
    source = image.convert("RGBA")
    tinted = Image.new("RGBA", source.size)
    src_px = source.load()
    out_px = tinted.load()
    for y in range(source.height):
        for x in range(source.width):
            r, g, b, a = src_px[x, y]
            if a < 20:
                out_px[x, y] = (0, 0, 0, 0)
            elif _is_dark_pixel(r, g, b, a):
                out_px[x, y] = (*BRAND_RGB, a)
            else:
                out_px[x, y] = (r, g, b, a)
    return tinted


def tint_icon_to_brand(image: Image.Image) -> Image.Image:
    """Red app icon with a white lightning cutout."""
    source = image.convert("RGBA")
    tinted = Image.new("RGBA", source.size, (*BRAND_RGB, 255))
    src_px = source.load()
    out_px = tinted.load()
    for y in range(source.height):
        for x in range(source.width):
            _r, _g, _b, a = src_px[x, y]
            if a >= 250:
                continue
            if a < 20:
                out_px[x, y] = (255, 255, 255, 255)
                continue
            t = 1.0 - (a / 255.0)
            out_px[x, y] = (
                int(255 * t + BRAND_RGB[0] * (1 - t)),
                int(255 * t + BRAND_RGB[1] * (1 - t)),
                int(255 * t + BRAND_RGB[2] * (1 - t)),
                255,
            )
    return tinted


def _resolve_source(path: str, fallback: str) -> str:
    if os.path.isfile(path):
        return path
    if os.path.isfile(fallback):
        return fallback
    raise FileNotFoundError(f"Brand asset not found: {path}")


def prepare_brand_assets():
    os.makedirs(BRAND_DIR, exist_ok=True)
    icon_source = _resolve_source(BRAND_ICON_SOURCE, BRAND_ICON)
    logo_source = _resolve_source(BRAND_LOGO_SOURCE, BRAND_LOGO)
    tint_icon_to_brand(Image.open(icon_source)).save(BRAND_ICON, "PNG")
    tint_logo_to_brand(Image.open(logo_source)).save(BRAND_LOGO, "PNG")


def _load_brand_icon() -> Image.Image:
    if not os.path.isfile(BRAND_ICON):
        prepare_brand_assets()
    return Image.open(BRAND_ICON).convert("RGBA")


def _render(size: int) -> Image.Image:
    source = _load_brand_icon()
    return source.resize((size, size), Image.Resampling.LANCZOS)


def _render_maskable(size: int) -> Image.Image:
    """Keep the lightning inside Android's 80% safe zone."""
    source = _load_brand_icon()
    canvas = Image.new("RGBA", (size, size), (*BRAND_RGB, 255))
    inner = int(size * 0.8)
    offset = (size - inner) // 2
    scaled = source.resize((inner, inner), Image.Resampling.LANCZOS)
    canvas.paste(scaled, (offset, offset), scaled)
    return canvas


def generate():
    prepare_brand_assets()
    os.makedirs(ICONS_DIR, exist_ok=True)
    for size, name in (
        (32, "favicon-32.png"),
        (180, "icon-180.png"),
        (192, "icon-192.png"),
        (512, "icon-512.png"),
    ):
        _render(size).save(os.path.join(ICONS_DIR, name), "PNG")
    for size, name in (
        (192, "icon-maskable-192.png"),
        (512, "icon-maskable-512.png"),
    ):
        _render_maskable(size).save(os.path.join(ICONS_DIR, name), "PNG")
    print("Icons generated from brand/icon.png")
    try:
        generate_demo_images()
    except Exception as e:
        print(f"Demo images skipped: {e}")


if __name__ == "__main__":
    generate()
