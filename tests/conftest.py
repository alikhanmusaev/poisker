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


def make_post_payload(**overrides):
    data = {
        "seller_name": TEST_SELLER_NAME,
        "title": "Тестовое объявление",
        "body": "Подробное описание товара для автотестов и проверки логики.",
        "category": "prodazha",
        "city": "grozny",
        "phone": "+79001234567",
    }
    data.update(overrides)
    return data


def create_test_post(app, *, publish=True, ip_hash="test", **overrides):
    from app.services.posts import create_post

    return create_post(make_post_payload(**overrides), ip_hash=ip_hash, publish=publish)


@pytest.fixture
def published_post(app):
    with app.app_context():
        return create_test_post(app, publish=True)


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


def set_captcha_session(client, answer: str, *, question: str = "test"):
    """Store a builtin captcha challenge in the test client session."""
    import time

    with client.session_transaction() as sess:
        sess["captcha_challenge"] = {
            "answer": answer,
            "question": question,
            "prompt": "Сколько будет",
            "kind": "math_digits",
            "expires": time.time() + 600,
        }


def fill_contact_reveals(client, post_ids):
    """Mark contact reveals in session to trigger CONTACT_SOFT_LIMIT captcha."""
    with client.session_transaction() as sess:
        sess["contact_revealed_posts"] = list(post_ids)
