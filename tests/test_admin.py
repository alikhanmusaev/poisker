"""Admin panel route and action tests."""

from app.models import AdminUser, Post
from tests.conftest import create_test_post


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
