"""Download third-party frontend assets into static/ (run after version bumps)."""

from __future__ import annotations

import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENDOR = ROOT / "static" / "vendor"
FONTS = ROOT / "static" / "fonts" / "inter"

HTMX_URL = "https://unpkg.com/htmx.org@2.0.4/dist/htmx.min.js"
LUCIDE_URL = "https://unpkg.com/lucide@0.468.0/dist/umd/lucide.min.js"
FONT_BASE = "https://cdn.jsdelivr.net/npm/@fontsource/inter@5.2.5/files"
FONT_FILES = (
    "inter-cyrillic-400-normal.woff2",
    "inter-cyrillic-500-normal.woff2",
    "inter-cyrillic-600-normal.woff2",
    "inter-cyrillic-700-normal.woff2",
    "inter-latin-400-normal.woff2",
    "inter-latin-500-normal.woff2",
    "inter-latin-600-normal.woff2",
    "inter-latin-700-normal.woff2",
)


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"  {dest.relative_to(ROOT)}")
    urllib.request.urlretrieve(url, dest)


def main() -> None:
    print("Vendor JS")
    download(HTMX_URL, VENDOR / "htmx.min.js")
    download(LUCIDE_URL, VENDOR / "lucide.min.js")

    print("Inter fonts")
    for name in FONT_FILES:
        download(f"{FONT_BASE}/{name}", FONTS / name)

    print("Done. inter.css is maintained in-repo.")


if __name__ == "__main__":
    main()
