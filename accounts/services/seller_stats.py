from datetime import timedelta

from django.db.models import Count, Q, Sum
from django.utils import timezone

from listings.models import Post
from messaging.models import Conversation


def annotate_seller_posts(queryset):
    """Add bookmark/conversation counts for seller post cards."""
    return queryset.annotate(
        bookmarks_count=Count("bookmarks", distinct=True),
        conversations_count=Count("conversations", distinct=True),
    )


def seller_stats_summary(user) -> dict:
    """Aggregate lifetime engagement for the seller cabinet."""
    posts = Post.objects.filter(user=user).exclude(status="deleted")
    now = timezone.now()
    agg = posts.aggregate(
        views_total=Sum("views"),
        contacts_total=Sum("contact_clicks"),
        bookmarks_total=Count("bookmarks", distinct=True),
        published_count=Count("id", filter=Q(status="published")),
        expiring_soon=Count(
            "id",
            filter=Q(
                status="published",
                expires_at__isnull=False,
                expires_at__lte=now + timedelta(days=3),
                expires_at__gt=now,
            ),
        ),
    )
    conversations_total = Conversation.objects.filter(seller=user).count()
    deals_confirmed = Conversation.objects.filter(
        seller=user,
        buyer_deal_confirmed_at__isnull=False,
        seller_deal_confirmed_at__isnull=False,
    ).count()

    views_total = int(agg["views_total"] or 0)
    contacts_total = int(agg["contacts_total"] or 0)
    contact_rate = round(contacts_total * 100 / views_total, 1) if views_total else None

    return {
        "views_total": views_total,
        "contacts_total": contacts_total,
        "conversations_total": conversations_total,
        "bookmarks_total": int(agg["bookmarks_total"] or 0),
        "published_count": int(agg["published_count"] or 0),
        "expiring_soon": int(agg["expiring_soon"] or 0),
        "deals_confirmed": deals_confirmed,
        "contact_rate": contact_rate,
        "rating_avg": getattr(user, "rating_avg", 0) or 0,
        "rating_count": int(getattr(user, "rating_count", 0) or 0),
    }


def days_until_expiry(post) -> int | None:
    if not post.expires_at or post.status != "published":
        return None
    delta = post.expires_at - timezone.now()
    if delta.total_seconds() <= 0:
        return 0
    return max(0, delta.days)
