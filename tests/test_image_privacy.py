"""Image watermark tests."""

import io

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
