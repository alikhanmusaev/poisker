import io
from unittest.mock import MagicMock, patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from listings.services.storage import (
    canonical_media_key,
    image_variant_url,
    upload_image,
    variant_key,
)


def test_variant_key_and_url():
    url = "/media/posts/abc123.jpg"
    assert variant_key(url, size="sm", fmt="jpeg") == "posts/abc123_sm.jpg"
    assert variant_key(url, size="full", fmt="webp") == "posts/abc123.webp"
    assert variant_key(url, size="sm", fmt="webp") == "posts/abc123_sm.webp"
    assert image_variant_url(url, size="sm", fmt="jpeg") == "/media/posts/abc123_sm.jpg"
    assert image_variant_url("/static/demo/x.jpg", size="sm") == "/static/demo/x.jpg"
    assert canonical_media_key("posts/abc123_sm.webp") == "posts/abc123.jpg"
    assert canonical_media_key("posts/abc123.webp") == "posts/abc123.jpg"


def _jpeg_bytes(size=(800, 600), color=(20, 80, 160)):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="JPEG", quality=90)
    return buf.getvalue()


@patch("listings.services.storage.schedule_variant_generation")
@patch("listings.services.storage._client")
def test_upload_image_writes_canonical_jpeg_only(mock_client, mock_schedule):
    client = MagicMock()
    mock_client.return_value = client
    uploaded = SimpleUploadedFile("shot.jpg", _jpeg_bytes(), content_type="image/jpeg")

    url = upload_image(uploaded, prefix="posts")
    assert url.startswith("/media/posts/")
    assert url.endswith(".jpg")
    assert client.put_object.call_count == 1
    key = client.put_object.call_args.kwargs["Key"]
    assert key.endswith(".jpg")
    assert "_sm" not in key
    mock_schedule.assert_called_once_with(url)


@patch("listings.services.storage._client")
def test_upload_image_schedules_background_variants(mock_client):
    client = MagicMock()
    mock_client.return_value = client
    uploaded = SimpleUploadedFile("shot.jpg", _jpeg_bytes(), content_type="image/jpeg")

    with patch("listings.services.storage.ensure_image_variants") as mock_variants:
        with patch("listings.services.storage.threading.Thread") as mock_thread:
            upload_image(uploaded, prefix="posts")
            mock_thread.assert_called_once()
            target = mock_thread.call_args.kwargs["target"]
            target()
            mock_variants.assert_called_once()
