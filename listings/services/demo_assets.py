"""Generate placeholder demo images for development seed."""

from pathlib import Path

from django.conf import settings
from PIL import Image, ImageDraw, ImageFont

from listings.constants import CATEGORIES, CATEGORY_LABELS

COLORS = {
    "nedvizhimost": "#0ea5e9",
    "avto": "#6366f1",
    "zapchasti": "#64748b",
    "elektronika": "#8b5cf6",
    "prodazha": "#ec4899",
    "dlya-doma": "#f59e0b",
    "uslugi": "#14b8a6",
    "rabota": "#22c55e",
    "detskie": "#f97316",
    "zhivotnye": "#a16207",
    "sport": "#ef4444",
    "stroitelstvo": "#78716c",
    "rasteniya": "#84cc16",
    "produkti": "#eab308",
    "biznes": "#0f766e",
    "drugoe": "#94a3b8",
}


def ensure_demo_images() -> int:
    demo_dir = Path(settings.BASE_DIR) / "static" / "demo"
    demo_dir.mkdir(parents=True, exist_ok=True)
    created = 0
    for slug in CATEGORIES:
        path = demo_dir / f"{slug}.jpg"
        if path.exists():
            continue
        color = COLORS.get(slug, "#64748b")
        img = Image.new("RGB", (640, 480), color)
        draw = ImageDraw.Draw(img)
        label = CATEGORY_LABELS.get(slug, slug)
        draw.rectangle([24, 24, 616, 456], outline="#ffffff", width=3)
        draw.text((48, 220), label, fill="#ffffff")
        img.save(path, format="JPEG", quality=85)
        created += 1
    return created


def demo_image_for(category: str) -> str:
    return f"/static/demo/{category}.jpg"
