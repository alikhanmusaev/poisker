"""Pytest bootstrap — never use the production database in tests."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Must run before `app.config` is imported (class attrs read env at import time).
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["RATELIMIT_STORAGE_URI"] = "memory://"
os.environ["RATELIMIT_ENABLED"] = "false"
os.environ["SCHEDULER_ENABLED"] = "false"
os.environ["TYPESENSE_URL"] = "http://127.0.0.1:1"
os.environ["PHONE_ENCRYPTION_KEY"] = "test-phone-encryption-key"
os.environ["HMAC_SECRET"] = "test-hmac-secret"

import pytest

from app import create_app
from app.extensions import db


TEST_SELLER_NAME = "Ахмад"


@pytest.fixture(autouse=True)
def noop_search_index(monkeypatch):
    def _noop_post(_post):
        return None

    def _noop_id(_post_id):
        return None

    for module in ("app.services.search", "app.services.posts", "app.services.seed", "app.routes.admin"):
        monkeypatch.setattr(f"{module}.index_post", _noop_post)
        monkeypatch.setattr(f"{module}.remove_post_from_index", _noop_id)


@pytest.fixture
def app():
    app = create_app("development")
    app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        RATELIMIT_ENABLED=False,
        SCHEDULER_ENABLED=False,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
    )
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()
