"""Builtin captcha provider."""

import time

from tests.conftest import set_captcha_session


def test_ensure_captcha_challenge_creates_question(app):
    from app.services.captcha import ensure_captcha_challenge

    with app.test_request_context("/"):
        app.config["REQUIRE_CAPTCHA"] = True
        question = ensure_captcha_challenge(force_new=True)
        assert question


def test_builtin_captcha_correct_answer_passes(app, client):
    from app.services.captcha import verify_captcha

    set_captcha_session(client, "12")
    with client.session_transaction() as sess:
        challenge = dict(sess["captcha_challenge"])
    with app.test_request_context("/"):
        from flask import session

        app.config["REQUIRE_CAPTCHA"] = True
        session["captcha_challenge"] = challenge
        assert verify_captcha("12") is True


def test_builtin_captcha_wrong_answer_fails(app, client):
    from app.services.captcha import verify_captcha

    set_captcha_session(client, "12")
    with client.session_transaction() as sess:
        challenge = dict(sess["captcha_challenge"])
    with app.test_request_context("/"):
        from flask import session

        app.config["REQUIRE_CAPTCHA"] = True
        session["captcha_challenge"] = challenge
        assert verify_captcha("99") is False


def test_builtin_captcha_clears_after_success(app, client):
    from app.services.captcha import SESSION_KEY, verify_captcha

    set_captcha_session(client, "7")
    with client.session_transaction() as sess:
        challenge = dict(sess["captcha_challenge"])
    with app.test_request_context("/"):
        from flask import session

        app.config["REQUIRE_CAPTCHA"] = True
        session["captcha_challenge"] = challenge
        assert verify_captcha("7") is True
        assert SESSION_KEY not in session
        assert verify_captcha("7") is False


def test_builtin_captcha_new_challenge_after_wrong_answer(app, client):
    from app.services.captcha import verify_captcha

    set_captcha_session(client, "12", question="2 + 3")
    with client.session_transaction() as sess:
        challenge = dict(sess["captcha_challenge"])
        old_question = challenge["question"]
    with app.test_request_context("/"):
        from flask import session

        app.config["REQUIRE_CAPTCHA"] = True
        session["captcha_challenge"] = challenge
        assert verify_captcha("wrong") is False
        new_question = session.get("captcha_challenge", {}).get("question")
        assert new_question
        assert new_question != old_question


def test_builtin_captcha_locks_after_max_failures(app, client):
    from app.services.captcha import is_captcha_locked, verify_captcha

    set_captcha_session(client, "5")
    with client.session_transaction() as sess:
        challenge = dict(sess["captcha_challenge"])
    with app.test_request_context("/"):
        from flask import session

        app.config["REQUIRE_CAPTCHA"] = True
        for _ in range(5):
            session["captcha_challenge"] = dict(challenge)
            session["captcha_challenge"]["expires"] = time.time() + 600
            verify_captcha("wrong")
        assert is_captcha_locked() is True
