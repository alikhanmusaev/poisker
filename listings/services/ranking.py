import math
import re
from datetime import datetime, timezone

from django.conf import settings
from django.utils import timezone as dj_timezone

from listings.models import Post


def utcnow():
    return dj_timezone.now()


def freshness_score(created_at: datetime, bumped_at: datetime | None = None) -> float:
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    reference = created_at
    if bumped_at:
        if bumped_at.tzinfo is None:
            bumped_at = bumped_at.replace(tzinfo=timezone.utc)
        if bumped_at > reference:
            reference = bumped_at
    age_hours = (utcnow() - reference).total_seconds() / 3600
    return math.exp(-age_hours / 72)


def completeness_score(post: Post) -> float:
    score = 0.0
    if post.has_photo:
        score += 0.4
    if post.images and len(post.images) >= 2:
        score += 0.2
    if post.price is not None:
        score += 0.2
    if len(post.body or "") >= 100:
        score += 0.1
    if 10 <= len(post.title or "") <= 50:
        score += 0.1
    return min(score, 1.0)


def spam_penalty(post: Post) -> float:
    penalty = 0.0
    title = post.title or ""
    body = post.body or ""
    if title.isupper() and len(title) > 10:
        penalty += 0.2
    if len(re.findall(r"https?://", body)) >= 2:
        penalty += 0.2
    words = body.lower().split()
    if words and len(words) != len(set(words)):
        penalty += 0.1
    return min(penalty, 0.5)


def trust_score(post: Post) -> float:
    penalty = spam_penalty(post)
    reports = post.reports_count or 0
    report_penalty = min(reports * 0.15, 0.6)
    return max(0.0, 1.0 - penalty - report_penalty)


def engagement_score(post: Post) -> float:
    views = math.log1p(post.views or 0) * 0.3
    clicks = math.log1p(post.contact_clicks or 0) * 0.7
    raw = views + clicks
    return min(raw / 3.0, 1.0)


def seller_reputation_score(user) -> float:
    """Bayesian-smoothed seller rating in 0..1. Neutral 0.5 without reviews."""
    if user is None:
        return 0.5
    count = int(getattr(user, "rating_count", 0) or 0)
    if count <= 0:
        return 0.5
    avg = float(getattr(user, "rating_avg", 0) or 0)
    prior_avg, prior_weight = 3.5, 3.0
    smoothed = (avg * count + prior_avg * prior_weight) / (count + prior_weight)
    return max(0.0, min(smoothed / 5.0, 1.0))


def active_paid_boost(post: Post) -> float:
    if post.paid_until and post.paid_until > utcnow():
        return post.paid_boost or 1.0
    return 1.0


def calculate_rank_score(post: Post) -> float:
    fresh = freshness_score(post.created_at, post.bumped_at)
    complete = completeness_score(post)
    trust = trust_score(post)
    engage = engagement_score(post)
    reputation = seller_reputation_score(getattr(post, "user", None))
    base = (
        fresh * 0.40
        + complete * 0.22
        + trust * 0.18
        + engage * 0.08
        + reputation * 0.12
    )
    return round(base * active_paid_boost(post), 4)


def recalculate_all_rank_scores():
    from django.db.models.signals import post_save

    from listings.signals import sync_search_index

    posts = list(Post.objects.filter(status="published").select_related("user"))
    if not posts:
        return 0
    for post in posts:
        post.rank_score = calculate_rank_score(post)
    post_save.disconnect(sync_search_index, sender=Post)
    try:
        Post.objects.bulk_update(posts, ["rank_score"], batch_size=200)
    finally:
        post_save.connect(sync_search_index, sender=Post)
    return len(posts)


def expire_old_posts():
    from bookmarks.services import notify_post_unpublished, notify_seller_expired
    from listings.services.search import remove_post_from_index

    now = utcnow()
    for post in Post.objects.filter(status="published", expires_at__lt=now):
        post.status = "expired"
        post.save(update_fields=["status"])
        remove_post_from_index(str(post.id))
        notify_post_unpublished(post)
        notify_seller_expired(post)


def maybe_auto_hide(post: Post):
    from bookmarks.services import notify_post_unpublished
    from listings.services.search import remove_post_from_index

    if post.reports_count >= settings.REPORTS_AUTO_HIDE_THRESHOLD and post.status == "published":
        post.status = "hidden"
        post.save(update_fields=["status"])
        remove_post_from_index(str(post.id))
        notify_post_unpublished(post)
