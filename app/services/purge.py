"""Hard-delete all posts and related listing data."""

from app.extensions import db
from app.models import PhoneDailyPublish, Post
from app.services.posts import hard_delete_post
from app.services.search import ensure_collection
from app.services.storage import purge_upload_prefix


def purge_all_posts(*, clear_daily_limits: bool = True) -> dict:
    """Remove every post (any status), uploaded images, search index docs, and daily limits."""
    posts = Post.query.order_by(Post.created_at.asc()).all()
    images_deleted = 0
    for post in posts:
        images_deleted += sum(1 for url in (post.images or []) if url.startswith("/media/"))
        hard_delete_post(post)

    orphan_objects = purge_upload_prefix()

    daily_cleared = 0
    if clear_daily_limits:
        daily_cleared = PhoneDailyPublish.query.delete()
        db.session.commit()

    ensure_collection(recreate=True)

    return {
        "posts_deleted": len(posts),
        "images_deleted": images_deleted,
        "orphan_objects_deleted": orphan_objects,
        "daily_limits_cleared": daily_cleared,
    }
