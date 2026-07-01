import io
import json
import logging
import uuid

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from flask import current_app
from PIL import Image, UnidentifiedImageError
from werkzeug.datastructures import FileStorage

logger = logging.getLogger(__name__)


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
        endpoint_url=current_app.config["S3_ENDPOINT"],
        aws_access_key_id=current_app.config["S3_ACCESS_KEY"],
        aws_secret_access_key=current_app.config["S3_SECRET_KEY"],
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def _log_exception(message: str):
    try:
        current_app.logger.exception(message)
    except RuntimeError:
        logger.exception(message)


def ensure_bucket():
    client = _client()
    bucket = current_app.config["S3_BUCKET"]
    try:
        client.head_bucket(Bucket=bucket)
    except Exception:
        try:
            client.create_bucket(Bucket=bucket)
        except Exception:
            _log_exception("Failed to create S3 bucket")

    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": ["*"]},
                "Action": ["s3:GetObject"],
                "Resource": [f"arn:aws:s3:::{bucket}/*"],
            }
        ],
    }
    try:
        client.put_bucket_policy(Bucket=bucket, Policy=json.dumps(policy))
    except Exception:
        _log_exception("Failed to set S3 bucket policy")


def _check_file_size(file: FileStorage) -> None:
    file.stream.seek(0, io.SEEK_END)
    size = file.stream.tell()
    file.stream.seek(0)
    max_size = current_app.config["MAX_UPLOAD_SIZE"]
    if size > max_size:
        raise ValueError(f"Файл слишком большой (макс. {max_size // (1024 * 1024)} МБ)")


def _validate_and_resize_image(file: FileStorage) -> bytes:
    max_pixels = current_app.config.get("MAX_IMAGE_PIXELS", 20_000_000)
    Image.MAX_IMAGE_PIXELS = max_pixels
    try:
        img = Image.open(file.stream)
        img.verify()
    except UnidentifiedImageError as exc:
        raise ValueError("Файл не является изображением") from exc
    except Image.DecompressionBombError as exc:
        raise ValueError("Изображение слишком большое") from exc

    file.stream.seek(0)
    img = Image.open(file.stream)
    if img.format not in current_app.config.get("ALLOWED_IMAGE_FORMATS", {"JPEG", "PNG", "WEBP"}):
        raise ValueError("Допустимые форматы: jpg, png, webp")

    width, height = img.size
    if width * height > max_pixels:
        raise ValueError("Изображение слишком большое")

    img = img.convert("RGB")
    max_size = (1200, 1200)
    img.thumbnail(max_size, Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85, optimize=True)
    buf.seek(0)
    return buf.read()


def upload_image(file: FileStorage) -> str:
    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    if ext not in current_app.config["ALLOWED_EXTENSIONS"]:
        raise ValueError("Допустимые форматы: jpg, png, webp")

    _check_file_size(file)
    data = _validate_and_resize_image(file)
    key = f"posts/{uuid.uuid4().hex}.jpg"
    bucket = current_app.config["S3_BUCKET"]
    client = _client()
    ensure_bucket()
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=data,
        ContentType="image/jpeg",
    )
    return f"/media/{key}"


def delete_stored_image(url: str) -> None:
    key = extract_s3_key(url)
    if not key:
        return
    bucket = current_app.config["S3_BUCKET"]
    try:
        _client().delete_object(Bucket=bucket, Key=key)
    except ClientError:
        _log_exception(f"Failed to delete S3 object: {key}")


def delete_stored_images(urls: list[str]) -> None:
    for url in urls:
        delete_stored_image(url)
