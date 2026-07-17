"""S3/MinIO image storage with full + thumb JPEG/WebP variants."""

from __future__ import annotations

import io
import logging
import re
import threading
import uuid
from pathlib import Path

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from PIL import Image, ImageOps, UnidentifiedImageError

logger = logging.getLogger(__name__)

JPEG_QUALITY = 62
JPEG_THUMB_QUALITY = 52
WEBP_QUALITY = 58
WEBP_THUMB_QUALITY = 48
MAX_DIMENSION = 960
THUMB_DIMENSION = 360
_WATERMARK_LOGO_PATH = Path(settings.BASE_DIR) / "static" / "brand" / "icon.png"

_VARIANT_RE = re.compile(
    r"^(?P<stem>.+?)(?P<sm>_sm)?\.(?P<ext>jpe?g|webp)$",
    re.IGNORECASE,
)


def extract_s3_key(url: str) -> str | None:
    if not url:
        return None
    if url.startswith("/media/"):
        return url.removeprefix("/media/")
    if "/posts/" in url:
        return "posts/" + url.split("/posts/", 1)[1]
    if "/messages/" in url:
        return "messages/" + url.split("/messages/", 1)[1]
    return None


def _client():
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def ensure_bucket():
    client = _client()
    bucket = settings.S3_BUCKET
    try:
        client.head_bucket(Bucket=bucket)
    except Exception:
        try:
            client.create_bucket(Bucket=bucket)
        except Exception:
            logger.exception("Failed to create S3 bucket")
    try:
        client.delete_bucket_policy(Bucket=bucket)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code not in ("NoSuchBucketPolicy", "NoSuchBucket"):
            logger.exception("Failed to make bucket private")


def _stem_from_key(key: str) -> str:
    """posts/abc_sm.webp -> posts/abc"""
    match = _VARIANT_RE.match(key)
    if not match:
        return key.rsplit(".", 1)[0]
    return match.group("stem")


def canonical_media_key(key: str) -> str:
    """Map any variant key to the DB-stored full JPEG key."""
    return f"{_stem_from_key(key)}.jpg"


def variant_key(key_or_url: str, *, size: str = "full", fmt: str = "jpeg") -> str:
    """Build a storage key for a size/format variant."""
    key = extract_s3_key(key_or_url) if "://" in key_or_url or key_or_url.startswith("/") else key_or_url
    if not key:
        return key_or_url
    stem = _stem_from_key(key)
    suffix = "_sm" if size == "sm" else ""
    ext = "webp" if fmt == "webp" else "jpg"
    return f"{stem}{suffix}.{ext}"


def image_variant_url(url: str, *, size: str = "full", fmt: str = "jpeg") -> str:
    """Derive a public /media URL for a variant. Non-media URLs pass through."""
    if not url or not str(url).startswith("/media/"):
        return url
    key = extract_s3_key(url)
    if not key:
        return url
    return f"/media/{variant_key(key, size=size, fmt=fmt)}"


def _encode_image(img: Image.Image, *, max_dim: int, fmt: str, quality: int) -> bytes:
    out = img.copy()
    out.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    if fmt == "webp":
        out.save(buf, format="WEBP", quality=quality, method=4)
    else:
        out.save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue()


def _variant_payloads(img: Image.Image) -> list[tuple[str, str, bytes]]:
    """Return (size, fmt, bytes) for all variants."""
    return [
        ("full", "jpeg", _encode_image(img, max_dim=MAX_DIMENSION, fmt="jpeg", quality=JPEG_QUALITY)),
        ("sm", "jpeg", _encode_image(img, max_dim=THUMB_DIMENSION, fmt="jpeg", quality=JPEG_THUMB_QUALITY)),
        ("full", "webp", _encode_image(img, max_dim=MAX_DIMENSION, fmt="webp", quality=WEBP_QUALITY)),
        ("sm", "webp", _encode_image(img, max_dim=THUMB_DIMENSION, fmt="webp", quality=WEBP_THUMB_QUALITY)),
    ]


def _content_type(fmt: str) -> str:
    return "image/webp" if fmt == "webp" else "image/jpeg"


def _put_bytes(key: str, data: bytes, content_type: str) -> None:
    _client().put_object(
        Bucket=settings.S3_BUCKET,
        Key=key,
        Body=data,
        ContentType=content_type,
    )


def _object_exists(key: str) -> bool:
    try:
        _client().head_object(Bucket=settings.S3_BUCKET, Key=key)
        return True
    except ClientError:
        return False


def _open_uploaded_rgb(uploaded: UploadedFile) -> Image.Image:
    if uploaded.size > settings.MAX_UPLOAD_SIZE:
        raise ValueError("Файл слишком большой (макс. 20 МБ).")
    Image.MAX_IMAGE_PIXELS = settings.MAX_IMAGE_PIXELS
    uploaded.seek(0)
    try:
        img = Image.open(uploaded)
        img.load()
        return ImageOps.exif_transpose(img).convert("RGB")
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError) as exc:
        raise ValueError("Недопустимое изображение") from exc


def schedule_variant_generation(url: str) -> None:
    """Build thumb/WebP variants off the request thread."""

    def _work() -> None:
        try:
            ensure_image_variants(url)
        except Exception:
            logger.exception("Background variant generation failed for %s", url)

    threading.Thread(target=_work, daemon=True, name="img-variants").start()


def upload_image(uploaded: UploadedFile, *, prefix: str = "posts") -> str:
    ext = (uploaded.name or "").rsplit(".", 1)[-1].lower()
    if ext not in settings.ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError("Допустимые форматы: jpg, png, webp")
    img = _open_uploaded_rgb(uploaded)
    stem = f"{prefix}/{uuid.uuid4().hex}"
    key = f"{stem}.jpg"
    try:
        data = _encode_image(img, max_dim=MAX_DIMENSION, fmt="jpeg", quality=JPEG_QUALITY)
        _put_bytes(key, data, "image/jpeg")
    except Exception as exc:
        logger.exception("S3 upload failed")
        raise ValueError("Хранилище временно недоступно.") from exc
    url = f"/media/{key}"
    schedule_variant_generation(url)
    return url


def ensure_variant_exists(key: str) -> None:
    """Create missing thumb/webp variants without requiring the caller to download bytes."""
    if _object_exists(key):
        return
    materialize_variant(key)


def materialize_variant(key: str) -> tuple[bytes, str]:
    """
    Ensure `key` exists in storage. If missing, build it from the canonical JPEG.
    Returns (bytes, content_type).
    """
    if _object_exists(key):
        return get_object_bytes(key)

    canon = canonical_media_key(key)
    if key == canon:
        return get_object_bytes(key)

    match = _VARIANT_RE.match(key)
    if not match:
        return get_object_bytes(key)

    size = "sm" if match.group("sm") else "full"
    fmt = "webp" if match.group("ext").lower() == "webp" else "jpeg"
    quality = {
        ("full", "jpeg"): JPEG_QUALITY,
        ("sm", "jpeg"): JPEG_THUMB_QUALITY,
        ("full", "webp"): WEBP_QUALITY,
        ("sm", "webp"): WEBP_THUMB_QUALITY,
    }[(size, fmt)]
    max_dim = THUMB_DIMENSION if size == "sm" else MAX_DIMENSION

    source, _ = get_object_bytes(canon)
    img = Image.open(io.BytesIO(source)).convert("RGB")
    data = _encode_image(img, max_dim=max_dim, fmt=fmt, quality=quality)
    try:
        _put_bytes(key, data, _content_type(fmt))
    except Exception:
        logger.exception("Failed to store materialized variant %s", key)
    return data, _content_type(fmt)


def ensure_image_variants(url: str, *, force: bool = False) -> int:
    """Create or refresh variants for a stored image URL. Returns count written."""
    key = extract_s3_key(url)
    if not key:
        return 0
    canon = canonical_media_key(key)
    if not _object_exists(canon):
        return 0
    source, _ = get_object_bytes(canon)
    img = Image.open(io.BytesIO(source)).convert("RGB")
    written = 0
    for size, fmt, data in _variant_payloads(img):
        vkey = variant_key(canon, size=size, fmt=fmt)
        if not force and vkey != canon and _object_exists(vkey):
            continue
        _put_bytes(vkey, data, _content_type(fmt))
        written += 1
    return written


def delete_stored_image(url: str) -> None:
    key = extract_s3_key(url)
    if not key:
        return
    canon = canonical_media_key(key)
    client = _client()
    for size in ("full", "sm"):
        for fmt in ("jpeg", "webp"):
            vkey = variant_key(canon, size=size, fmt=fmt)
            try:
                client.delete_object(Bucket=settings.S3_BUCKET, Key=vkey)
            except ClientError:
                logger.exception("Failed to delete S3 object %s", vkey)


def get_object_bytes(key: str) -> tuple[bytes, str]:
    obj = _client().get_object(Bucket=settings.S3_BUCKET, Key=key)
    return obj["Body"].read(), obj.get("ContentType") or "image/jpeg"


def generate_presigned_get_url(key: str, *, expires: int = 900) -> str | None:
    """
    Return a short-lived GET URL for browsers when S3_PUBLIC_URL points at a
    reachable MinIO/S3 host. Returns None when signing is unavailable or the
    public endpoint looks like an internal docker hostname.
    """
    public = (settings.S3_PUBLIC_URL or "").rstrip("/")
    if not public or "minio:" in public or public.startswith("http://minio"):
        return None
    app_domain = (getattr(settings, "APP_DOMAIN", "") or "").strip().lower()
    public_lower = public.lower()
    if app_domain and f"://{app_domain}" in public_lower:
        return None
    if app_domain and f"://www.{app_domain}" in public_lower:
        return None
    endpoint = public.rsplit("/", 1)[0] if "/" in public[8:] else public
    try:
        client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            config=Config(signature_version="s3v4"),
            region_name="us-east-1",
        )
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.S3_BUCKET, "Key": key},
            ExpiresIn=expires,
        )
    except Exception:
        logger.exception("Failed to sign S3 GET for %s", key)
        return None
