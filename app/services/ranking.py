import math
import re
from datetime import datetime, timedelta, timezone

from zoneinfo import ZoneInfo

from flask import current_app

from app.constants import REPORTS_AUTO_HIDE_THRESHOLD
from app.models import Post, utcnow


MSK = ZoneInfo("Europe/Moscow")


def start_of_today_msk() -> datetime:
    now_msk = datetime.now(MSK)
    start = now_msk.replace(hour=0, minute=0, second=0, microsecond=0)
    return start.astimezone(timezone.utc)


def today_msk_date():
    return datetime.now(MSK).date()


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
    if 10 <= len(post.title or "") <= 80:
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


def active_paid_boost(post: Post) -> float:
    if post.paid_until and post.paid_until > utcnow():
        return post.paid_boost or 1.0
    return 1.0


def calculate_rank_score(post: Post) -> float:
    fresh = freshness_score(post.created_at, post.bumped_at)
    complete = completeness_score(post)
    trust = trust_score(post)
    engage = engagement_score(post)
    base = fresh * 0.45 + complete * 0.25 + trust * 0.20 + engage * 0.10
    return round(base * active_paid_boost(post), 4)


def recalculate_all_rank_scores():
    from app.extensions import db

    posts = Post.query.filter_by(status="published").all()
    for post in posts:
        post.rank_score = calculate_rank_score(post)
    db.session.commit()


def expire_old_posts():
    from app.extensions import db
    from app.services.search import remove_post_from_index

    now = utcnow()
    expired = Post.query.filter(Post.status == "published", Post.expires_at < now).all()
    for post in expired:
        post.status = "expired"
        remove_post_from_index(post.id)
    db.session.commit()


def apply_promotion(post: Post, promo_type: str):
    from app.constants import PROMOTION_TYPES
    from app.extensions import db

    if promo_type not in PROMOTION_TYPES:
        raise ValueError("Неизвестный тип продвижения")

    _, boost, hours = PROMOTION_TYPES[promo_type]
    now = utcnow()
    post.paid_boost = boost
    post.bumped_at = now
    post.paid_until = now + timedelta(hours=hours)
    post.rank_score = calculate_rank_score(post)
    db.session.commit()


def maybe_auto_hide(post: Post):
    from app.extensions import db
    from app.services.search import remove_post_from_index

    if post.reports_count >= REPORTS_AUTO_HIDE_THRESHOLD and post.status == "published":
        post.status = "hidden"
        remove_post_from_index(post.id)
        db.session.commit()
