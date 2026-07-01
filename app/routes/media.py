"""Proxy uploaded images from MinIO/S3."""

from botocore.exceptions import ClientError
from flask import Blueprint, Response, abort, current_app

from app.services.storage import _client, extract_s3_key

bp = Blueprint("media", __name__)


def resolve_image_url(url: str) -> str:
    from flask import url_for

    key = extract_s3_key(url)
    if key:
        return url_for("media.serve", key=key)
    return url or ""


@bp.route("/media/<path:key>")
def serve(key: str):
    if not key.startswith("posts/"):
        abort(404)
    bucket = current_app.config["S3_BUCKET"]
    try:
        obj = _client().get_object(Bucket=bucket, Key=key)
    except ClientError:
        abort(404)

    return Response(
        obj["Body"],
        mimetype=obj.get("ContentType") or "image/jpeg",
        headers={"Cache-Control": "public, max-age=86400"},
    )
