import random
import time

from flask import current_app, session

SESSION_KEY = "captcha_challenge"


def captcha_provider() -> str:
    return "builtin"


def captcha_required() -> bool:
    if current_app.config.get("REQUIRE_CAPTCHA") is not None:
        return bool(current_app.config.get("REQUIRE_CAPTCHA"))
    return bool(current_app.config.get("REQUIRE_TURNSTILE"))


def captcha_enabled() -> bool:
    return captcha_required()


def captcha_site_key() -> str:
    return ""


def _captcha_ttl() -> int:
    return int(current_app.config.get("CAPTCHA_TTL_SECONDS", 600))


def _challenge_valid(challenge: dict | None) -> bool:
    return bool(challenge and challenge.get("expires", 0) > time.time())


def ensure_captcha_challenge(*, force_new: bool = False) -> str:
    challenge = session.get(SESSION_KEY)
    if not force_new and _challenge_valid(challenge):
        return challenge["question"]

    a, b = random.randint(2, 12), random.randint(2, 12)
    question = f"{a} + {b}"
    session[SESSION_KEY] = {
        "answer": str(a + b),
        "question": question,
        "expires": time.time() + _captcha_ttl(),
    }
    session.modified = True
    return question


def new_captcha_question() -> str:
    return ensure_captcha_challenge(force_new=True)


def _verify_builtin(answer: str) -> bool:
    challenge = session.get(SESSION_KEY)
    if not _challenge_valid(challenge):
        return False
    if not answer:
        return False
    if answer.strip() != challenge.get("answer"):
        return False
    session.pop(SESSION_KEY, None)
    session.modified = True
    return True


def verify_captcha(response: str, remote_ip: str | None = None) -> bool:
    del remote_ip
    if not captcha_required():
        return True
    return _verify_builtin(response)


def verify_turnstile(token: str, remote_ip: str | None = None) -> bool:
    return verify_captcha(token, remote_ip)


def extract_captcha_response() -> str:
    from flask import request

    return request.form.get("captcha_answer", "") or request.headers.get("X-Captcha-Answer", "")


def extract_captcha_token() -> str:
    return extract_captcha_response()
