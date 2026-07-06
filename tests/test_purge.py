"""Hard purge of all posts."""

from unittest.mock import patch

from tests.conftest import create_test_post


def test_purge_all_posts_removes_every_status(app):
    from app.models import PhoneDailyPublish, Post
    from app.services.posts import delete_post
    from app.services.purge import purge_all_posts

    with app.app_context():
        published = create_test_post(app, publish=True, phone="+79001112233")
        pending = create_test_post(app, publish=False, phone="+79001112244")
        deleted = create_test_post(app, publish=True, phone="+79001112255")
        delete_post(deleted)
        deleted.images = ["/media/posts/test.jpg"]
        Post.query.session.commit()

        PhoneDailyPublish.query.delete()
        Post.query.session.commit()

        with patch("app.services.posts.delete_stored_images"):
            with patch("app.services.purge.purge_upload_prefix", return_value=1):
                with patch("app.services.purge.ensure_collection") as ensure_mock:
                    stats = purge_all_posts()

        assert stats["posts_deleted"] == 3
        assert Post.query.count() == 0
        ensure_mock.assert_called_once_with(recreate=True)
