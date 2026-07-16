from datetime import timedelta

import logging

from django.conf import settings
from django.utils import timezone

from listings.models import Post
from listings.services.search import remove_post_from_index
from listings.services.storage import delete_stored_image

logger = logging.getLogger(__name__)


def cleanup_deleted_posts(retention_days=None, batch_size=None) -> dict:
    retention_days = retention_days or settings.DELETED_POST_RETENTION_DAYS
    batch_size = batch_size or getattr(settings, "DELETED_POST_CLEANUP_BATCH_SIZE", 100)
    cutoff = timezone.now() - timedelta(days=retention_days)
    posts = list(
        Post.objects.filter(status="deleted", deleted_at__isnull=False, deleted_at__lt=cutoff).order_by("deleted_at")[
            :batch_size
        ]
    )
    processed = images_deleted = 0
    for post in posts:
        for url in list(post.images or []):
            try:
                delete_stored_image(url)
                images_deleted += 1
            except Exception:
                logger.exception("cleanup image %s", url)
        post.images = []
        post.has_photo = False
        post.cover_index = 0
        post.save(update_fields=["images", "has_photo", "cover_index"])
        remove_post_from_index(str(post.pk))
        processed += 1
    return {"processed": processed, "images_deleted": images_deleted}
