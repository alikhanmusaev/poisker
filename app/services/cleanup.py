"""Cleanup of soft-deleted posts after retention period."""

from datetime import timedelta

from flask import current_app

from app.extensions import db
from app.models import Post, utcnow
from app.services.search import remove_post_from_index
from app.services.storage import delete_stored_image


def cleanup_deleted_posts(retention_days=None, batch_size=None) -> dict:
    """Purge images and encrypted phone from deleted posts older than retention_days."""
    if retention_days is None:
        retention_days = current_app.config["DELETED_POST_RETENTION_DAYS"]
    if batch_size is None:
        batch_size = current_app.config["DELETED_POST_CLEANUP_BATCH_SIZE"]

    cutoff = utcnow() - timedelta(days=retention_days)
    posts = (
        Post.query.filter(
            Post.status == "deleted",
            Post.deleted_at.isnot(None),
            Post.deleted_at < cutoff,
        )
        .order_by(Post.deleted_at.asc())
        .limit(batch_size)
        .all()
    )

    processed = 0
    images_deleted = 0
    phone_encrypted_cleared = 0

    for post in posts:
        for url in list(post.images or []):
            try:
                delete_stored_image(url)
                images_deleted += 1
            except Exception:
                current_app.logger.exception(
                    "cleanup: failed to delete image %s for post %s", url, post.id
                )

        post.images = []
        post.has_photo = False
        post.cover_index = 0

        if post.phone_encrypted is not None:
            post.phone_encrypted = None
            phone_encrypted_cleared += 1

        try:
            remove_post_from_index(post.id)
        except Exception:
            current_app.logger.exception(
                "cleanup: failed to remove post %s from search index", post.id
            )

        post.updated_at = utcnow()
        processed += 1

    if processed:
        db.session.commit()

    return {
        "processed": processed,
        "images_deleted": images_deleted,
        "phone_encrypted_cleared": phone_encrypted_cleared,
    }
