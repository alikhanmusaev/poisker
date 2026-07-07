"""Report flow and auto-hide moderation."""

from app.constants import REPORTS_AUTO_HIDE_THRESHOLD
from app.services.ranking import maybe_auto_hide
from tests.conftest import create_test_post


def test_maybe_auto_hide_hides_post_at_threshold(app):
    with app.app_context():
        post = create_test_post(app, publish=True, phone="+79003001001")
        post.reports_count = REPORTS_AUTO_HIDE_THRESHOLD
        maybe_auto_hide(post)
        assert post.status == "hidden"


def test_maybe_auto_hide_ignores_below_threshold(app):
    with app.app_context():
        post = create_test_post(app, publish=True, phone="+79003001002")
        post.reports_count = REPORTS_AUTO_HIDE_THRESHOLD - 1
        maybe_auto_hide(post)
        assert post.status == "published"


def test_maybe_auto_hide_ignores_non_published(app):
    with app.app_context():
        post = create_test_post(app, publish=False, phone="+79003001003")
        post.reports_count = REPORTS_AUTO_HIDE_THRESHOLD
        maybe_auto_hide(post)
        assert post.status == "pending"
