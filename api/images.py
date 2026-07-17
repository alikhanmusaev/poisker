from concurrent.futures import ThreadPoolExecutor

from listings.services.storage import upload_image


def upload_files(files) -> list[str]:
    items = [f for f in files if f][:5]
    if not items:
        return []
    if len(items) == 1:
        return [upload_image(items[0])]
    workers = min(len(items), 3)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(upload_image, items))


def resolve_image_updates(existing: list[str], remove_indices: set[int], new_files, cover_index: int, old_cover_index: int):
    if not remove_indices and not new_files:
        return None

    kept = [url for i, url in enumerate(existing) if i not in remove_indices]
    new_keys = upload_files(new_files)
    images = (kept + new_keys)[:5]

    if new_keys:
        cover_new = max(0, min(cover_index, len(new_keys) - 1))
        cover_index = len(kept) + cover_new
    else:
        old_url = existing[old_cover_index] if existing and 0 <= old_cover_index < len(existing) else None
        if old_url and old_url in kept:
            cover_index = kept.index(old_url)
        else:
            cover_index = 0

    if images:
        cover_index = max(0, min(cover_index, len(images) - 1))
    else:
        cover_index = 0
    return images, cover_index
