"""S3/MinIO image storage."""

import io
import logging
import uuid
from functools import lru_cache
from pathlib import Path

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError

logger = logging.getLogger(__name__)
JPEG_QUALITY = 82
MAX_DIMENSION = 1200
_WATERMARK_LOGO_PATH = Path(settings.BASE_DIR) / "static" / "brand" / "icon.png"


def extract_s3_key(url: str) -> str | None:
    if not url:
        return None
    if url.startswith("/media/"):
        return url.removeprefix("/media/")
    if "/posts/" in url:
        return "posts/" + url.split("/posts/", 1)[1]
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


def _validate_and_resize_image(uploaded: UploadedFile) -> bytes:
    if uploaded.size > settings.MAX_UPLOAD_SIZE:
        raise ValueError("Файл слишком большой (макс. 5 МБ).")
    Image.MAX_IMAGE_PIXELS = settings.MAX_IMAGE_PIXELS
    try:
        img = Image.open(uploaded)
        img.verify()
    except (UnidentifiedImageError, Image.DecompressionBombError) as exc:
        raise ValueError("Недопустимое изображение") from exc
    uploaded.seek(0)
    img = Image.open(uploaded).convert("RGB")
    img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    buf.seek(0)
    return buf.read()


def upload_image(uploaded: UploadedFile, *, prefix: str = "posts") -> str:
    ext = (uploaded.name or "").rsplit(".", 1)[-1].lower()
    if ext not in settings.ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError("Допустимые форматы: jpg, png, webp")
    data = _validate_and_resize_image(uploaded)
    key = f"{prefix}/{uuid.uuid4().hex}.jpg"
    try:
        _client().put_object(Bucket=settings.S3_BUCKET, Key=key, Body=data, ContentType="image/jpeg")
    except Exception as exc:
        logger.exception("S3 upload failed")
        raise ValueError("Хранилище временно недоступно.") from exc
    return f"/media/{key}"


def delete_stored_image(url: str) -> None:
    key = extract_s3_key(url)
    if not key:
        return
    try:
        _client().delete_object(Bucket=settings.S3_BUCKET, Key=key)
    except ClientError:
        logger.exception("Failed to delete S3 object %s", key)


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
    # Public URL is typically https://host/bucket or http://host:9000/bucket
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
