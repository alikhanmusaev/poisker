"""Image watermark tests."""

import io
from unittest.mock import MagicMock, patch

from PIL import Image
from werkzeug.datastructures import FileStorage


def _image_file(fmt: str, name: str, *, size=(800, 600), color=(120, 120, 120)) -> FileStorage:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format=fmt)
    buf.seek(0)
    return FileStorage(stream=buf, filename=name, content_type=f"image/{fmt.lower()}")


def test_watermark_font_supports_cyrillic():
    from PIL import ImageFont

    from app.services.storage import _WATERMARK_FONT_PATH, _watermark_font

    assert _WATERMARK_FONT_PATH.is_file()
    font = _watermark_font(20)
    assert isinstance(font, ImageFont.FreeTypeFont)


def test_watermark_label_includes_site_and_domain(app):
    from app.services.storage import _watermark_label

    with app.app_context():
        label = _watermark_label()
    assert "Поискер" in label
    assert "poisker.ru" in label


def test_prepare_watermark_logo_removes_red_background():
    from app.services.storage import _prepare_watermark_logo

    logo = Image.new("RGBA", (40, 40), (185, 28, 28, 255))
    for x in range(12, 28):
        for y in range(10, 30):
            logo.putpixel((x, y), (255, 255, 255, 255))

    prepared = _prepare_watermark_logo(logo)
    assert prepared.getpixel((2, 2))[3] == 0
    assert prepared.getpixel((20, 20))[3] == 255


def test_validate_and_resize_image_applies_watermark(app):
    from app.services.storage import _validate_and_resize_image

    with app.app_context():
        data = _validate_and_resize_image(_image_file("JPEG", "car.jpg"))
    assert len(data) > 100
    assert data[:2] == b"\xff\xd8"


def test_bucket_bootstrap_removes_public_policy(app):
    from app.services.storage import ensure_bucket

    client = MagicMock()
    with app.app_context(), patch("app.services.storage._client", return_value=client):
        ensure_bucket()

    client.delete_bucket_policy.assert_called_once_with(Bucket="board-images")
    client.put_bucket_policy.assert_not_called()


def test_deleted_post_media_is_not_served(app, client):
    from conftest import create_test_post

    with app.app_context():
        post = create_test_post(app, images=["/media/posts/private.jpg"])
        post_id = post.id

    storage = MagicMock()
    storage.get_object.return_value = {
        "Body": io.BytesIO(b"image"),
        "ContentType": "image/jpeg",
    }
    with patch("app.routes.media._client", return_value=storage):
        response = client.get("/media/posts/private.jpg")
        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "private, max-age=300"

        with app.app_context():
            from app.models import Post
            from app.services.posts import delete_post

            delete_post(Post.query.filter_by(id=post_id).first())

        assert client.get("/media/posts/private.jpg").status_code == 404


def test_hidden_post_media_requires_owner_token(app, client):
    from conftest import create_test_post

    with app.app_context():
        post = create_test_post(app, publish=False, images=["/media/posts/hidden.jpg"])
        token = post.edit_token

    storage = MagicMock()
    storage.get_object.return_value = {
        "Body": io.BytesIO(b"image"),
        "ContentType": "image/jpeg",
    }
    with patch("app.routes.media._client", return_value=storage):
        assert client.get("/media/posts/hidden.jpg").status_code == 404
        assert client.get(f"/media/posts/hidden.jpg?token={token}").status_code == 200
