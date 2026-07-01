import io
import json
import uuid

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from flask import current_app
from PIL import Image
from werkzeug.datastructures import FileStorage


Image.MAX_IMAGE_PIXELS = 20_000_000


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


def ensure_bucket():
    client = _client()
    bucket = current_app.config["S3_BUCKET"]
    try:
        client.head_bucket(Bucket=bucket)
    except Exception:
        client.create_bucket(Bucket=bucket)

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
        pass


def _check_file_size(file: FileStorage) -> None:
    file.stream.seek(0, io.SEEK_END)
    size = file.stream.tell()
    file.stream.seek(0)
    max_size = current_app.config["MAX_UPLOAD_SIZE"]
    if size > max_size:
        raise ValueError(f"Файл слишком большой (макс. {max_size // (1024 * 1024)} МБ)")


def _resize_image(file: FileStorage) -> bytes:
    img = Image.open(file.stream)
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
    data = _resize_image(file)
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
        pass


def delete_stored_images(urls: list[str]) -> None:
    for url in urls:
        delete_stored_image(url)
