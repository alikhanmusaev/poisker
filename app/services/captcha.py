import random
import time

import httpx
from flask import current_app, session

YANDEX_VALIDATE_URL = "https://smartcaptcha.cloud.yandex.ru/validate"
TURNSTILE_VALIDATE_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
SESSION_KEY = "captcha_challenge"


def captcha_provider() -> str:
    return (current_app.config.get("CAPTCHA_PROVIDER") or "builtin").lower()


def captcha_required() -> bool:
    if current_app.config.get("REQUIRE_CAPTCHA") is not None:
        return bool(current_app.config.get("REQUIRE_CAPTCHA"))
    return bool(current_app.config.get("REQUIRE_TURNSTILE"))


def captcha_enabled() -> bool:
    return captcha_required() and captcha_provider() not in ("none", "")


def captcha_site_key() -> str:
    provider = captcha_provider()
    if provider == "turnstile":
        return current_app.config.get("TURNSTILE_SITE_KEY", "")
    if provider == "yandex":
        return current_app.config.get("SMARTCAPTCHA_SITE_KEY", "")
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
    challenge = session.pop(SESSION_KEY, None)
    session.modified = True
    if not _challenge_valid(challenge):
        return False
    if not answer:
        return False
    return answer.strip() == challenge.get("answer")


def _verify_yandex(token: str, remote_ip: str | None) -> bool:
    secret = current_app.config.get("SMARTCAPTCHA_SECRET_KEY", "")
    if not secret:
        return False
    if not token:
        return False

    data = {"secret": secret, "token": token}
    if remote_ip:
        data["ip"] = remote_ip

    try:
        with httpx.Client(timeout=10) as client:
            resp = client.post(YANDEX_VALIDATE_URL, data=data)
            result = resp.json()
            return result.get("status") == "ok"
    except httpx.HTTPError:
        return False


def _verify_turnstile(token: str, remote_ip: str | None) -> bool:
    secret = current_app.config.get("TURNSTILE_SECRET_KEY", "")
    if not secret:
        return False
    if not token:
        return False

    data = {"secret": secret, "response": token}
    if remote_ip:
        data["remoteip"] = remote_ip

    try:
        with httpx.Client(timeout=10) as client:
            resp = client.post(TURNSTILE_VALIDATE_URL, data=data)
            result = resp.json()
            return bool(result.get("success"))
    except httpx.HTTPError:
        return False


def verify_captcha(response: str, remote_ip: str | None = None) -> bool:
    provider = captcha_provider()
    if provider == "none" or not captcha_required():
        return True
    if provider == "builtin":
        return _verify_builtin(response)
    if provider == "turnstile":
        return _verify_turnstile(response, remote_ip)
    if provider == "yandex":
        return _verify_yandex(response, remote_ip)
    return False


def verify_turnstile(token: str, remote_ip: str | None = None) -> bool:
    return verify_captcha(token, remote_ip)


def extract_captcha_response() -> str:
    from flask import request

    return (
        request.form.get("captcha_answer", "")
        or request.headers.get("X-Captcha-Answer", "")
        or request.headers.get("X-Captcha-Token", "")
        or request.headers.get("X-Turnstile-Token", "")
        or request.form.get("smart-token", "")
        or request.form.get("cf-turnstile-response", "")
    )


def extract_captcha_token() -> str:
    """Backward-compatible alias."""
    return extract_captcha_response()
