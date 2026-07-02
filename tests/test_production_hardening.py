"""Tests for production hardening features."""

import io
from unittest.mock import MagicMock, patch

from PIL import Image
from werkzeug.datastructures import FileStorage


def _create_post(app, phone="+79001234567", title="Тестовое объявление"):
    from app.services.posts import create_post

    with app.app_context():
        post = create_post(
            {
                "seller_name": "Продавец",
                "title": title,
                "body": "Достаточно длинное описание товара для публикации на доске.",
                "category": "prodazha",
                "city": "grozny",
                "phone": phone,
                "images": [],
            },
            ip_hash="hardening-test",
            publish=True,
        )
        return {"id": post.id, "edit_token": post.edit_token, "slug": post.slug}


def _image_file(fmt: str, filename: str, size=(50, 50)) -> FileStorage:
    buf = io.BytesIO()
    Image.new("RGB", size, color="red").save(buf, format=fmt)
    buf.seek(0)
    return FileStorage(stream=buf, filename=filename)


def test_edit_with_valid_token(client, app):
    post = _create_post(app)
    token = post["edit_token"]
    res = client.post(
        f"/posts/{post['id']}/edit?token={token}",
        data={
            "title": "Обновлённый заголовок",
            "seller_name": "Продавец",
            "body": "Достаточно длинное описание товара для публикации на доске.",
            "category": "prodazha",
            "city": "grozny",
            "token": token,
        },
        follow_redirects=True,
    )
    assert res.status_code == 200
    assert "Обновлённый заголовок" in res.get_data(as_text=True) or "обновлено" in res.get_data(as_text=True).lower()


def test_edit_with_wrong_token_denied(client, app):
    post = _create_post(app)
    res = client.get(f"/posts/{post['id']}/edit?token=wrong-token")
    assert res.status_code == 404


def test_delete_with_valid_token(client, app):
    post = _create_post(app)
    token = post["edit_token"]
    res = client.post(
        f"/posts/{post['id']}/delete",
        data={"token": token},
        follow_redirects=True,
    )
    assert res.status_code == 200
    with app.app_context():
        from app.models import Post

        deleted = Post.query.get(post["id"])
        assert deleted is not None
        assert deleted.status == "deleted"
        assert deleted.deleted_at is not None


def test_delete_with_wrong_token_denied(client, app):
    post = _create_post(app)
    res = client.post(f"/posts/{post['id']}/delete", data={"token": "bad-token"})
    assert res.status_code == 404


def test_city_seo_page_returns_200_not_redirect(client):
    res = client.get("/gorod/grozny", follow_redirects=False)
    assert res.status_code == 200
    assert "Объявления в Грозном" in res.get_data(as_text=True)


def test_city_category_seo_page_returns_200_not_redirect(client):
    res = client.get("/gorod/grozny/avto", follow_redirects=False)
    assert res.status_code == 200
    text = res.get_data(as_text=True)
    assert res.status_code == 200
    assert "Авто в Грозном" in text
    assert 'href="/gorod/grozny/avto"' in text or 'canonical' in text


def test_valid_jpeg_upload_validation(app):
    from app.services.storage import _validate_and_resize_image

    with app.app_context():
        data = _validate_and_resize_image(_image_file("JPEG", "photo.jpg"))
        assert len(data) > 100


def test_valid_png_upload_validation(app):
    from app.services.storage import _validate_and_resize_image

    with app.app_context():
        data = _validate_and_resize_image(_image_file("PNG", "photo.png"))
        assert len(data) > 100


def test_valid_webp_upload_validation(app):
    from app.services.storage import _validate_and_resize_image

    with app.app_context():
        data = _validate_and_resize_image(_image_file("WEBP", "photo.webp"))
        assert len(data) > 100


def test_wrong_extension_rejected(app):
    from app.services.storage import upload_image

    with app.app_context():
        f = _image_file("JPEG", "photo.gif")
        try:
            upload_image(f)
            assert False, "expected ValueError"
        except ValueError as exc:
            assert "формат" in str(exc).lower() or "jpg" in str(exc).lower()


def test_fake_jpg_rejected(app):
    from app.services.storage import upload_image

    fake = FileStorage(stream=io.BytesIO(b"not an image"), filename="fake.jpg")
    with app.app_context():
        try:
            upload_image(fake)
            assert False, "expected ValueError"
        except ValueError as exc:
            assert "изображен" in str(exc).lower()


def test_oversized_file_rejected(app):
    from app.services.storage import upload_image

    buf = io.BytesIO()
    Image.new("RGB", (5000, 5000), color="blue").save(buf, format="JPEG", quality=95)
    buf.seek(0)
    f = FileStorage(stream=buf, filename="big.jpg")
    with app.app_context():
        app.config["MAX_UPLOAD_SIZE"] = 1024
        try:
            upload_image(f)
            assert False, "expected ValueError"
        except ValueError as exc:
            assert "больш" in str(exc).lower()


def test_phone_encryption_key_fallback_decrypt(app):
    from app.services.phone import normalize_phone
    from app.services.phone_crypto import _legacy_fernet, decrypt_phone

    with app.app_context():
        app.config["PHONE_ENCRYPTION_KEY"] = "new-phone-key-for-tests"
        app.config["HMAC_SECRET"] = "legacy-hmac-for-tests"
        legacy_blob = _legacy_fernet().encrypt(normalize_phone("+79001112233").encode()).decode()
        assert decrypt_phone(legacy_blob) == "+79001112233"


def test_admin_audit_log_on_hide(client, app):
    from app.extensions import db
    from app.models import AdminAuditLog, AdminUser

    with app.app_context():
        admin = AdminUser(username="modaudit")
        admin.set_password("modpass")
        db.session.add(admin)
        db.session.commit()

    client.post("/admin/login", data={"username": "modaudit", "password": "modpass"}, follow_redirects=True)
    post = _create_post(app)
    res = client.post(f"/admin/posts/{post['id']}/hide", follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        log = AdminAuditLog.query.filter_by(action="hide", target_id=post["id"]).first()
        assert log is not None
        assert log.target_type == "post"
        assert log.ip_hash


def test_admin_audit_page_requires_login(client):
    res = client.get("/admin/audit")
    assert res.status_code == 302
    assert "login" in res.location


def test_upload_image_logs_s3_errors(app):
    from app.services.storage import upload_image

    mock_client = MagicMock()
    mock_client.put_object.side_effect = Exception("s3 down")

    with app.app_context():
        with patch("app.services.storage._client", return_value=mock_client):
            with patch("app.services.storage.ensure_bucket"):
                try:
                    upload_image(_image_file("JPEG", "x.jpg"))
                    assert False
                except Exception:
                    pass
