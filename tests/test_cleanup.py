"""Cleanup of soft-deleted posts and user-facing unpublish flow."""

from datetime import timedelta
from unittest.mock import patch

import pytest

from tests.conftest import create_test_post


def _make_deleted_post(app, *, days_ago=31, images=None, phone_encrypted=None, publish=True):
    from app.extensions import db
    from app.models import Post, utcnow
    from app.services.posts import delete_post

    with app.app_context():
        post = create_test_post(app, publish=publish)
        if images is not None:
            post.images = images
            post.has_photo = bool(images)
        if phone_encrypted is not None:
            post.phone_encrypted = phone_encrypted
        db.session.commit()

        delete_post(post)

        post = Post.query.get(post.id)
        past = utcnow() - timedelta(days=days_ago)
        post.deleted_at = past
        post.updated_at = past
        db.session.commit()
        return post.id


def test_soft_delete_keeps_images_and_phone_encrypted(app):
    from app.extensions import db
    from app.models import Post
    from app.services.posts import delete_post

    images = ["/media/test/photo.jpg"]
    with app.app_context():
        post = create_test_post(app, publish=True)
        post.images = images
        post.has_photo = True
        post.phone_encrypted = "encrypted-phone"
        db.session.commit()
        post_id = post.id
        phone_encrypted = post.phone_encrypted

        delete_post(post)

        stored = Post.query.get(post_id)
        assert stored.status == "deleted"
        assert stored.deleted_at is not None
        assert stored.images == images
        assert stored.phone_encrypted == phone_encrypted


def test_cleanup_ignores_recent_deleted_posts(app):
    from app.models import Post
    from app.services.cleanup import cleanup_deleted_posts

    post_id = _make_deleted_post(app, days_ago=5, images=["/media/a.jpg"], phone_encrypted="enc")

    with app.app_context():
        with patch("app.services.cleanup.delete_stored_image") as delete_mock:
            stats = cleanup_deleted_posts(retention_days=30, batch_size=100)

        post = Post.query.get(post_id)
        assert stats["processed"] == 0
        assert post.images == ["/media/a.jpg"]
        assert post.phone_encrypted == "enc"
        delete_mock.assert_not_called()


def test_cleanup_clears_old_deleted_posts(app):
    from app.models import Post
    from app.services.cleanup import cleanup_deleted_posts

    post_id = _make_deleted_post(
        app,
        days_ago=31,
        images=["/media/a.jpg", "/media/b.jpg"],
        phone_encrypted="enc",
    )

    with app.app_context():
        with patch("app.services.cleanup.delete_stored_image") as delete_mock:
            with patch("app.services.cleanup.remove_post_from_index") as index_mock:
                stats = cleanup_deleted_posts(retention_days=30, batch_size=100)

        post = Post.query.get(post_id)
        assert stats == {"processed": 1, "images_deleted": 2, "phone_encrypted_cleared": 1}
        assert post.status == "deleted"
        assert post.images == []
        assert post.has_photo is False
        assert post.cover_index == 0
        assert post.phone_encrypted is None
        assert post.phone_hash
        assert post.phone_masked
        assert post.title
        assert delete_mock.call_count == 2
        index_mock.assert_called_once_with(post_id)


def test_cleanup_ignores_published_posts(app):
    from app.extensions import db
    from app.models import Post, utcnow
    from app.services.cleanup import cleanup_deleted_posts

    with app.app_context():
        post = create_test_post(app, publish=True)
        post.images = ["/media/old.jpg"]
        post.phone_encrypted = "enc"
        post.created_at = utcnow() - timedelta(days=60)
        db.session.commit()
        post_id = post.id

        with patch("app.services.cleanup.delete_stored_image") as delete_mock:
            stats = cleanup_deleted_posts(retention_days=30, batch_size=100)

        post = Post.query.get(post_id)
        assert stats["processed"] == 0
        assert post.status == "published"
        assert post.images == ["/media/old.jpg"]
        assert post.phone_encrypted == "enc"
        delete_mock.assert_not_called()


def test_cleanup_is_idempotent(app):
    from app.models import Post
    from app.services.cleanup import cleanup_deleted_posts

    post_id = _make_deleted_post(app, days_ago=40, images=["/media/a.jpg"], phone_encrypted="enc")

    with app.app_context():
        with patch("app.services.cleanup.delete_stored_image"):
            stats_first = cleanup_deleted_posts(retention_days=30, batch_size=100)
            stats_second = cleanup_deleted_posts(retention_days=30, batch_size=100)

        post = Post.query.get(post_id)
        assert stats_first["processed"] == 1
        assert stats_second["processed"] == 1
        assert post.images == []
        assert post.phone_encrypted is None


def test_cleanup_cli_command(app):
    runner = app.test_cli_runner()

    with app.app_context():
        _make_deleted_post(app, days_ago=35, images=["/media/a.jpg"], phone_encrypted="enc")

    with patch("app.services.cleanup.delete_stored_image"):
        result = runner.invoke(args=["cleanup-deleted-posts", "--days", "30", "--batch-size", "100"])

    assert result.exit_code == 0
    assert "Processed: 1" in result.output
    assert "Images deleted: 1" in result.output
    assert "Phones cleared: 1" in result.output


def test_user_delete_flash_message(client, app):
    post = create_test_post(app, publish=True)
    with app.app_context():
        token = post.edit_token
        post_id = post.id

    res = client.post(
        f"/posts/{post_id}/delete",
        data={"token": token},
        follow_redirects=True,
    )
    assert res.status_code == 200
    assert "Объявление снято с публикации" in res.get_data(as_text=True)
