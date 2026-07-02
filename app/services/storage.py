import io
import json
import logging
import uuid
from functools import lru_cache
from pathlib import Path

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from flask import current_app
from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError
from werkzeug.datastructures import FileStorage

logger = logging.getLogger(__name__)

JPEG_QUALITY = 82
MAX_DIMENSION = 1200
_WATERMARK_LOGO_PATH = Path(__file__).resolve().parent.parent / "static" / "brand" / "icon.png"


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


def _watermark_font(size: int):
    for name in ("DejaVuSans-Bold.ttf", "DejaVuSans.ttf", "arialbd.ttf", "arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


@lru_cache(maxsize=1)
def _watermark_logo_image() -> Image.Image | None:
    try:
        logo = Image.open(_WATERMARK_LOGO_PATH).convert("RGBA")
        return _prepare_watermark_logo(logo)
    except OSError:
        logger.warning("Watermark logo not found at %s", _WATERMARK_LOGO_PATH)
        return None


def _prepare_watermark_logo(logo: Image.Image) -> Image.Image:
    """Keep only the white mark; drop solid red/black background."""
    pixels = logo.load()
    width, height = logo.size
    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            if r > 120 and r > g + 25 and r > b + 25:
                pixels[x, y] = (r, g, b, 0)
            elif r < 45 and g < 45 and b < 45:
                pixels[x, y] = (r, g, b, 0)
            elif r > 200 and g > 200 and b > 200:
                pixels[x, y] = (255, 255, 255, 255)
    return logo


def _scaled_logo(height: int) -> Image.Image | None:
    logo = _watermark_logo_image()
    if logo is None or height < 1:
        return None
    ratio = logo.width / logo.height
    width = max(1, int(height * ratio))
    return logo.resize((width, height), Image.Resampling.LANCZOS)


def _apply_watermark(img: Image.Image) -> Image.Image:
    site = (current_app.config.get("SITE_NAME") or "Поискер").strip()
    short_side = min(img.size)
    logo_h = max(18, min(42, short_side // 16))
    font_size = max(13, min(30, short_side // 22))
    font = _watermark_font(font_size)

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    bbox = draw.textbbox((0, 0), site, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    pad_x = max(10, short_side // 70)
    pad_y = max(8, short_side // 90)
    gap = max(8, short_side // 100)
    margin = max(10, short_side // 36)
    radius = max(8, short_side // 50)

    logo_img = _scaled_logo(logo_h)
    logo_w = logo_img.width if logo_img else 0
    if logo_img is None:
        gap = 0

    content_w = logo_w + (gap if logo_img else 0) + text_w
    content_h = max(logo_h, text_h)
    badge_w = content_w + pad_x * 2
    badge_h = content_h + pad_y * 2

    x0 = img.width - badge_w - margin
    y0 = img.height - badge_h - margin
    draw.rounded_rectangle(
        [x0, y0, x0 + badge_w, y0 + badge_h],
        radius=radius,
        fill=(15, 23, 42, 175),
    )

    if logo_img:
        logo_x = x0 + pad_x
        logo_y = y0 + (badge_h - logo_h) // 2
        overlay.paste(logo_img, (logo_x, logo_y), logo_img)
        text_x = logo_x + logo_w + gap
    else:
        text_x = x0 + pad_x

    text_y = y0 + (badge_h - text_h) // 2 - bbox[1]
    draw.text((text_x, text_y), site, fill=(255, 255, 255, 245), font=font)

    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def _validate_and_resize_image(file: FileStorage, *, category: str | None = None) -> bytes:
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
    img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.Resampling.LANCZOS)

    if current_app.config.get("PLATE_BLUR_ENABLED", True):
        from app.services.image_privacy import blur_license_plates

        img = blur_license_plates(img, category=category)

    img = _apply_watermark(img)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
    buf.seek(0)
    return buf.read()


def upload_image(file: FileStorage, *, category: str | None = None) -> str:
    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    if ext not in current_app.config["ALLOWED_EXTENSIONS"]:
        raise ValueError("Допустимые форматы: jpg, png, webp")

    _check_file_size(file)
    data = _validate_and_resize_image(file, category=category)
    key = f"posts/{uuid.uuid4().hex}.jpg"
    bucket = current_app.config["S3_BUCKET"]
    client = _client()
    try:
        client.put_object(
            Bucket=bucket,
            Key=key,
            Body=data,
            ContentType="image/jpeg",
        )
    except Exception as exc:
        _log_exception("Failed to upload image to storage")
        raise ValueError("Хранилище временно недоступно. Попробуйте позже.") from exc
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
