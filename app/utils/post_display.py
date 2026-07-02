"""Helpers for public post display (cover order, pending revisions)."""


def ordered_images(post, images=None) -> list[str]:
    images = list(images if images is not None else (post.images or []))
    if not images:
        return []
    cover = getattr(post, "cover_index", 0) or 0
    cover = min(max(int(cover), 0), len(images) - 1)
    return [images[cover]] + [img for i, img in enumerate(images) if i != cover]


def cover_image(post, images=None) -> str | None:
    ordered = ordered_images(post, images=images)
    return ordered[0] if ordered else None


def has_pending_revision(post) -> bool:
    return bool(getattr(post, "pending_revision", None))


def form_values_for_edit(post) -> dict:
    """Values shown in owner edit form (pending draft if awaiting review)."""
    rev = post.pending_revision or {}
    return {
        "title": rev.get("title", post.title),
        "body": rev.get("body", post.body),
        "images": list(rev.get("images", post.images or [])),
        "cover_index": int(rev.get("cover_index", getattr(post, "cover_index", 0) or 0)),
    }
