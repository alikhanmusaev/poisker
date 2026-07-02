"""Image watermark and license plate blur tests."""

import io

import pytest
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


def test_blur_license_plates_skips_non_auto_category(app):
    from app.services.image_privacy import blur_license_plates

    img = Image.new("RGB", (400, 300), (100, 100, 100))
    with app.app_context():
        result = blur_license_plates(img, category="nedvizhimost")
    assert result is img


def test_blur_license_plates_does_not_crash_for_auto(app):
    from app.services.image_privacy import blur_license_plates

    img = Image.new("RGB", (640, 480), (90, 90, 90))
    with app.app_context():
        result = blur_license_plates(img, category="avto")
    assert result.size == img.size


def test_validate_and_resize_image_applies_watermark(app):
    from app.services.storage import _validate_and_resize_image

    with app.app_context():
        data = _validate_and_resize_image(_image_file("JPEG", "car.jpg"), category="prodazha")
    assert len(data) > 100
    assert data[:2] == b"\xff\xd8"


@pytest.fixture
def opencv_available():
    pytest.importorskip("cv2")


def test_blur_license_plates_does_not_blur_plain_car_photo(app, opencv_available):
    import numpy as np

    from app.services.image_privacy import blur_license_plates

    # Uniform car body without a plate-like rectangle — should stay unchanged.
    arr = np.full((600, 800, 3), 145, dtype=np.uint8)
    img = Image.fromarray(arr)

    with app.app_context():
        result = blur_license_plates(img, category="avto")

    assert np.array_equal(np.array(img), np.array(result))


def test_blur_license_plates_only_blurs_small_plate_region(app, opencv_available):
    import cv2
    import numpy as np

    from app.services.image_privacy import blur_license_plates

    arr = np.full((600, 800, 3), 145, dtype=np.uint8)
    cv2.rectangle(arr, (330, 500), (470, 530), (245, 245, 245), -1)
    cv2.putText(arr, "A123BC95", (340, 524), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (25, 25, 25), 2)
    img = Image.fromarray(arr)

    with app.app_context():
        result = blur_license_plates(img, category="avto")

    orig = np.array(img)
    blurred = np.array(result)
    # Plate area changed
    assert not np.array_equal(orig[495:535, 325:475], blurred[495:535, 325:475])
    # Upper part of the car unchanged
    assert np.array_equal(orig[100:300, 200:600], blurred[100:300, 200:600])


def test_blur_license_plates_finds_rectangular_region(app, opencv_available):
    import cv2
    import numpy as np

    from app.services.image_privacy import blur_license_plates

    arr = np.full((600, 800, 3), 145, dtype=np.uint8)
    cv2.rectangle(arr, (330, 500), (470, 530), (245, 245, 245), -1)
    cv2.putText(arr, "A123BC95", (340, 524), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (25, 25, 25), 2)
    img = Image.fromarray(arr)

    with app.app_context():
        result = blur_license_plates(img, category="avto")

    orig = np.array(img)
    blurred = np.array(result)
    assert not np.array_equal(orig[495:535, 325:475], blurred[495:535, 325:475])
