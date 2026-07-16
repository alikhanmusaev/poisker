from urllib.parse import urlparse

from django.db.models import F
from django.urls import reverse

from listings.constants import CATEGORY_LABELS, CITIES
from listings.models import Post
from listings.utils.post_display import ordered_images


def increment_views(post: Post) -> None:
    Post.objects.filter(pk=post.pk).update(views=F("views") + 1)
    post.views = (post.views or 0) + 1


def build_show_context(request, post: Post) -> dict:
    referrer = request.META.get("HTTP_REFERER", "")
    back_url = reverse("core:index")
    if referrer:
        parsed = urlparse(referrer)
        host = request.get_host()
        if parsed.netloc == host and parsed.path in ("", "/"):
            back_url = referrer

    from bookmarks.services import is_post_bookmarked

    return {
        "post": post,
        "gallery_images": ordered_images(post),
        "back_url": back_url,
        "category_labels": CATEGORY_LABELS,
        "cities": CITIES,
        "is_bookmarked": is_post_bookmarked(request.user, post),
    }
