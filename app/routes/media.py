"""Proxy uploaded images from MinIO/S3."""

from botocore.exceptions import ClientError
from flask import Blueprint, Response, abort, current_app, request, url_for
from flask_login import current_user
from sqlalchemy import String, cast

from app.models import Post
from app.services.posts import is_post_publicly_visible
from app.services.storage import _client, extract_s3_key

bp = Blueprint("media", __name__)


def resolve_image_url(url: str) -> str:
    key = extract_s3_key(url)
    if key:
        token = request.args.get("token", "")
        if token:
            return url_for("media.serve", key=key, token=token)
        return url_for("media.serve", key=key)
    if url and url.startswith("/static/"):
        separator = "&" if "?" in url else "?"
        return f"{url}{separator}v={current_app.config.get('STATIC_VERSION', '1')}"
    return url or ""


def _posts_referencing_key(key: str) -> list[Post]:
    # Cross-database textual pre-filter, followed by an exact key comparison.
    candidates = Post.query.filter(cast(Post.images, String).contains(key)).all()
    return [
        post
        for post in candidates
        if any(extract_s3_key(url) == key for url in (post.images or []))
    ]


def _may_serve(key: str) -> bool:
    token = request.args.get("token", "")
    for post in _posts_referencing_key(key):
        if current_user.is_authenticated:
            return True
        if is_post_publicly_visible(post):
            return True
        if token and post.edit_token == token and post.status in ("pending", "hidden"):
            return True
    return False


@bp.route("/media/<path:key>")
def serve(key: str):
    if not key.startswith("posts/"):
        abort(404)
    if not _may_serve(key):
        abort(404)
    bucket = current_app.config["S3_BUCKET"]
    try:
        obj = _client().get_object(Bucket=bucket, Key=key)
    except ClientError:
        abort(404)

    return Response(
        obj["Body"],
        mimetype=obj.get("ContentType") or "image/jpeg",
        headers={"Cache-Control": "private, max-age=300"},
    )
