"""Static asset cache-busting helpers."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path


def _watched_static_files(static_root: Path) -> list[Path]:
    names = (
        "css/style.css",
        "css/admin.css",
        "js/app.js",
        "js/admin.js",
        "js/home.js",
        "brand/logo.png",
        "brand/icon.png",
        "icons/favicon-32.png",
        "icons/icon-180.png",
        "icons/icon-192.png",
        "icons/icon-512.png",
        "icons/icon-maskable-192.png",
        "icons/icon-maskable-512.png",
    )
    watched = [static_root / name for name in names if (static_root / name).is_file()]
    watched.extend(sorted((static_root / "demo").glob("*.jpg")))
    return watched


def compute_static_version(static_folder: str | None) -> str:
    configured = os.getenv("STATIC_VERSION", "").strip()
    if configured:
        return configured
    if not static_folder:
        return "1"
    static_root = Path(static_folder)
    digest = hashlib.sha256()
    for path in sorted(_watched_static_files(static_root)):
        stat = path.stat()
        digest.update(path.as_posix().encode())
        digest.update(str(int(stat.st_mtime_ns)).encode())
        digest.update(str(stat.st_size).encode())
    return digest.hexdigest()[:12]
