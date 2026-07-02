"""Admin panel route and action tests."""

from datetime import timedelta

from app.models import AdminUser, Post, utcnow
from app.services.phone import generate_edit_token
from app.services.posts import make_unique_slug
from app.services.ranking import calculate_rank_score
from tests.conftest import create_test_post


def _duplicate_post_same_phone(app, source_post_id, *, title="Второе", status="pending"):
    with app.app_context():
        from app.extensions import db

        source_post = Post.query.get(source_post_id)
        now = utcnow()
        post = Post(
            title=title,
            seller_name=source_post.seller_name,
            body=source_post.body,
            category=source_post.category,
            city=source_post.city,
            price=source_post.price,
            phone_hash=source_post.phone_hash,
            phone_masked=source_post.phone_masked,
            phone_encrypted=source_post.phone_encrypted,
            edit_token=generate_edit_token(),
            status=status,
            images=[],
            has_photo=False,
            created_at=now,
            expires_at=now + timedelta(days=30),
            bumped_at=now,
        )
        db.session.add(post)
        db.session.flush()
        post.slug = make_unique_slug(title, post.id)
        post.rank_score = calculate_rank_score(post)
        db.session.commit()
        return post.id


def _login_admin(client, app, username="admintest", password="admintestpass"):
    with app.app_context():
        if not AdminUser.query.filter_by(username=username).first():
            admin = AdminUser(username=username)
            admin.set_password(password)
            from app.extensions import db

            db.session.add(admin)
            db.session.commit()
    return client.post(
        "/admin/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )


def test_admin_requires_login(client):
    assert client.get("/admin/").status_code == 302
    assert client.get("/admin/posts").status_code == 302
    assert client.get("/admin/moderation").status_code == 302
    assert client.get("/admin/reports").status_code == 302


def test_admin_dashboard_accessible(client, app):
    _login_admin(client, app)
    res = client.get("/admin/")
    assert res.status_code == 200
    assert "Обзор" in res.get_data(as_text=True)
    assert "Быстрые действия" in res.get_data(as_text=True)


def test_admin_posts_page(client, app):
    _login_admin(client, app)
    res = client.get("/admin/posts")
    assert res.status_code == 200
    assert "Объявления" in res.get_data(as_text=True)


def test_admin_moderation_page(client, app):
    _login_admin(client, app)
    res = client.get("/admin/moderation")
    assert res.status_code == 200
    assert "Модерация" in res.get_data(as_text=True)


def test_admin_reports_page(client, app):
    _login_admin(client, app)
    res = client.get("/admin/reports")
    assert res.status_code == 200
    assert "Жалобы" in res.get_data(as_text=True)


def test_admin_delete_soft_deletes_post(client, app):
    with app.app_context():
        post = create_test_post(app, publish=True, phone="+79008887766")
        post_id = post.id
    _login_admin(client, app)
    res = client.post(f"/admin/posts/{post_id}/delete", follow_redirects=True)
    assert res.status_code == 200
    with app.app_context():
        refreshed = Post.query.get(post_id)
        assert refreshed.status == "deleted"


def test_admin_hide_changes_status(client, app):
    with app.app_context():
        post = create_test_post(app, publish=True, phone="+79008887755")
        post_id = post.id
    _login_admin(client, app)
    client.post(f"/admin/posts/{post_id}/hide", follow_redirects=True)
    with app.app_context():
        assert Post.query.get(post_id).status == "hidden"


def test_admin_publish_changes_status(client, app):
    with app.app_context():
        post = create_test_post(app, publish=False, phone="+79008887744")
        post_id = post.id
        assert post.status == "pending"
    _login_admin(client, app)
    client.post(f"/admin/posts/{post_id}/publish", follow_redirects=True)
    with app.app_context():
        assert Post.query.get(post_id).status == "published"


def test_admin_logout_get_not_allowed(client, app):
    _login_admin(client, app)
    assert client.get("/admin/logout").status_code == 405


def test_admin_logout_post_works(client, app):
    _login_admin(client, app)
    res = client.post("/admin/logout", follow_redirects=False)
    assert res.status_code in (302, 303)


def test_admin_posts_phone_filter_finds_post(client, app):
    phone = "+79007776655"
    with app.app_context():
        post = create_test_post(app, publish=True, phone=phone)
        post_id = post.id
    _login_admin(client, app)
    res = client.get(f"/admin/posts?phone=%2B79007776655")
    text = res.get_data(as_text=True)
    assert res.status_code == 200
    assert post_id[:8] in text or post.title[:20] in text


def test_admin_posts_invalid_phone_filter(client, app):
    _login_admin(client, app)
    res = client.get("/admin/posts?phone=abc", follow_redirects=True)
    assert res.status_code == 200
    assert "Некорректный номер" in res.get_data(as_text=True)


def test_block_phone_hides_all_active_posts(client, app):
    phone = "+79006665544"
    with app.app_context():
        post1 = create_test_post(app, publish=True, phone=phone, title="Первое спам объявление")
        id1 = post1.id
    id2 = _duplicate_post_same_phone(app, id1, title="Второе спам объявление", status="pending")
    _login_admin(client, app)
    client.post(f"/admin/posts/{id1}/block-phone", follow_redirects=True)
    with app.app_context():
        assert Post.query.get(id1).status == "hidden"
        assert Post.query.get(id2).status == "hidden"


def test_block_phone_does_not_change_deleted(client, app):
    phone = "+79005554433"
    with app.app_context():
        from app.services.posts import delete_post

        active = create_test_post(app, publish=True, phone=phone, title="Активное")
        active_id = active.id
    deleted_id = _duplicate_post_same_phone(app, active_id, title="Удалённое", status="published")
    with app.app_context():
        delete_post(Post.query.get(deleted_id))
    _login_admin(client, app)
    client.post(f"/admin/posts/{active_id}/block-phone", follow_redirects=True)
    with app.app_context():
        assert Post.query.get(active_id).status == "hidden"
        assert Post.query.get(deleted_id).status == "deleted"


def test_admin_preview_deleted_shows_banner(client, app):
    with app.app_context():
        from app.services.posts import delete_post

        post = create_test_post(app, publish=True, phone="+79004443322")
        post_id = post.id
        delete_post(post)
    _login_admin(client, app)
    res = client.get(f"/admin/posts/{post_id}/preview")
    text = res.get_data(as_text=True)
    assert res.status_code == 200
    assert "Админ-предпросмотр" in text
    assert "удалённое объявление" in text.lower()
