"""Helpers for public post display (cover order, pending revisions)."""


def ordered_images(post, images=None) -> list[str]:
    images = list(images if images is not None else (post.images or []))
    if not images:
        return []
    cover = getattr(post, "cover_index", 0) or 0
    cover = min(max(int(cover), 0), len(images) - 1)
    return [images[cover]] + [img for i, img in enumerate(images) if i != cover]
