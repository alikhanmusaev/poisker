"""Admin panel query helpers."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import or_

from app.extensions import db
from app.models import BlockedPhone, Post, Promotion, Report


def parse_admin_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.strptime(value.strip(), "%Y-%m-%d")
        return parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def filter_posts_query(
    *,
    status: str | None = None,
    q: str | None = None,
    city: str | None = None,
    category: str | None = None,
    has_photo: bool = False,
    has_reports: bool = False,
    date_from: str | None = None,
    date_to: str | None = None,
    revisions_only: bool = False,
):
    query = Post.query
    if revisions_only:
        query = query.filter(Post.pending_revision.isnot(None))
    elif status and status != "all":
        query = query.filter_by(status=status)

    term = (q or "").strip()
    if term:
        like = f"%{term}%"
        query = query.filter(
            or_(
                Post.title.ilike(like),
                Post.body.ilike(like),
                Post.phone_masked.ilike(like),
            )
        )
    if city:
        query = query.filter_by(city=city)
    if category:
        query = query.filter_by(category=category)
    if has_photo:
        query = query.filter(Post.has_photo.is_(True))
    if has_reports:
        query = query.filter(Post.reports_count > 0)

    start = parse_admin_date(date_from)
    end = parse_admin_date(date_to)
    if start:
        query = query.filter(Post.created_at >= start)
    if end:
        end_exclusive = end.replace(hour=23, minute=59, second=59)
        query = query.filter(Post.created_at <= end_exclusive)

    return query.order_by(Post.created_at.desc())


def paginate_query(query, page: int, per_page: int = 30):
    return query.paginate(page=max(page, 1), per_page=per_page, error_out=False)


def count_posts_by_status() -> dict[str, int]:
    rows = db.session.query(Post.status, db.func.count(Post.id)).group_by(Post.status).all()
    counts = {status: count for status, count in rows}
    counts["total"] = sum(counts.values())
    return counts


def count_reports(*, new_only: bool = False) -> int:
    query = Report.query
    if new_only:
        query = query.filter_by(status="new")
    return query.count()


def posts_count_for_phone(phone_hash: str) -> int:
    return Post.query.filter_by(phone_hash=phone_hash).count()


def blocked_phone_rows(page: int, per_page: int = 30):
    pagination = BlockedPhone.query.order_by(BlockedPhone.created_at.desc()).paginate(
        page=max(page, 1), per_page=per_page, error_out=False
    )
    rows = []
    for blocked in pagination.items:
        rows.append(
            {
                "blocked": blocked,
                "posts_count": posts_count_for_phone(blocked.phone_hash),
            }
        )
    return rows, pagination


def filter_reports_query(*, status: str | None = None, reason: str | None = None, date_from: str | None = None):
    query = Report.query
    if status and status != "all":
        query = query.filter_by(status=status)
    if reason:
        query = query.filter_by(reason=reason)
    start = parse_admin_date(date_from)
    if start:
        query = query.filter(Report.created_at >= start)
    return query.order_by(Report.created_at.desc())


def filter_promotions_query(status: str | None = None):
    query = Promotion.query
    if status and status != "all":
        query = query.filter_by(status=status)
    return query.order_by(Promotion.created_at.desc())


def revision_diff(post: Post) -> dict | None:
    revision = post.pending_revision
    if not revision:
        return None
    changes = []
    if revision.get("title") and revision.get("title") != post.title:
        changes.append({"field": "title", "old": post.title, "new": revision["title"]})
    if revision.get("body") and revision.get("body") != post.body:
        changes.append({"field": "body", "old": post.body, "new": revision["body"]})
    old_images = post.images or []
    new_images = revision.get("images") or old_images
    if new_images != old_images:
        changes.append(
            {
                "field": "images",
                "old": f"{len(old_images)} фото",
                "new": f"{len(new_images)} фото",
            }
        )
    return {"revision": revision, "changes": changes}
