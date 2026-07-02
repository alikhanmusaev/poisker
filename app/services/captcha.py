import random
import re
import time

from flask import current_app, session

SESSION_KEY = "captcha_challenge"
FAILURES_KEY = "captcha_failures"
CONTACT_REVEALS_KEY = "contact_revealed_posts"
MAX_FAILURES = 5
FAILURE_WINDOW = 600

NUM_WORDS = {
    "ноль": 0,
    "один": 1,
    "одна": 1,
    "два": 2,
    "две": 2,
    "три": 3,
    "четыре": 4,
    "пять": 5,
    "шесть": 6,
    "семь": 7,
    "восемь": 8,
    "девять": 9,
    "десять": 10,
    "одиннадцать": 11,
    "двенадцать": 12,
    "тринадцать": 13,
    "четырнадцать": 14,
    "пятнадцать": 15,
}

WORD_ANSWERS = ("поискер", "рынок")


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


def is_captcha_locked() -> bool:
    now = time.time()
    failures = [t for t in (session.get(FAILURES_KEY) or []) if now - t < FAILURE_WINDOW]
    session[FAILURES_KEY] = failures
    session.modified = True
    return len(failures) >= MAX_FAILURES


def _record_failure() -> None:
    now = time.time()
    failures = [t for t in (session.get(FAILURES_KEY) or []) if now - t < FAILURE_WINDOW]
    failures.append(now)
    session[FAILURES_KEY] = failures
    session.modified = True


def captcha_error_message() -> str:
    if is_captcha_locked():
        return "Слишком много попыток. Попробуйте позже."
    return "Подтвердите, что вы не робот"


def captcha_prompt() -> str:
    challenge = session.get(SESSION_KEY) or {}
    return challenge.get("prompt", "Проверка")


def _number_to_words(n: int) -> str:
    for word, value in NUM_WORDS.items():
        if value == n:
            return word
    return str(n)


def generate_builtin_challenge() -> dict:
    kind = random.choice(("math_digits", "math_words", "number_word", "word"))
    if kind == "math_digits":
        a, b = random.randint(2, 12), random.randint(2, 12)
        op = random.choice(("+", "-"))
        if op == "-" and b > a:
            a, b = b, a
        answer = str(a + b if op == "+" else a - b)
        question = f"{a} {op} {b}"
        prompt = "Сколько будет"
    elif kind == "math_words":
        a, b = random.randint(2, 12), random.randint(2, 12)
        op = random.choice(("+", "-"))
        if op == "-" and b > a:
            a, b = b, a
        answer = str(a + b if op == "+" else a - b)
        op_word = "плюс" if op == "+" else "минус"
        question = f"{_number_to_words(a)} {op_word} {_number_to_words(b)}"
        prompt = "Сколько будет"
    elif kind == "number_word":
        n = random.randint(0, 15)
        answer = str(n)
        question = _number_to_words(n)
        prompt = "Введите цифрами число:"
    else:
        answer = random.choice(WORD_ANSWERS)
        question = answer
        prompt = "Введите слово:"
    return {"question": question, "answer": answer, "prompt": prompt, "kind": kind}


def _store_challenge(challenge: dict) -> None:
    session[SESSION_KEY] = {
        "answer": challenge["answer"],
        "question": challenge["question"],
        "prompt": challenge.get("prompt", "Проверка"),
        "kind": challenge.get("kind", "math_digits"),
        "expires": time.time() + _captcha_ttl(),
    }
    session.modified = True


def ensure_captcha_challenge(*, force_new: bool = False) -> str:
    if is_captcha_locked():
        return captcha_error_message()
    challenge = session.get(SESSION_KEY)
    if not force_new and _challenge_valid(challenge):
        return challenge["question"]
    generated = generate_builtin_challenge()
    _store_challenge(generated)
    return generated["question"]


def new_captcha_question() -> str:
    return ensure_captcha_challenge(force_new=True)


def _normalize_answer(value: str, kind: str) -> str:
    text = (value or "").strip()
    if kind == "word":
        return text.casefold()
    if kind == "number":
        digits = re.sub(r"\D", "", text)
        return digits
    return text


def _verify_builtin(answer: str) -> bool:
    if is_captcha_locked():
        return False
    challenge = session.get(SESSION_KEY)
    if not _challenge_valid(challenge):
        return False
    if answer is None:
        return False
    kind = challenge.get("kind", "math_digits")
    expected = _normalize_answer(challenge.get("answer", ""), kind)
    given = _normalize_answer(answer, kind)
    if not given:
        return False
    if given != expected:
        return False
    session.pop(SESSION_KEY, None)
    session[FAILURES_KEY] = []
    session.modified = True
    return True


def verify_captcha(response: str, remote_ip: str | None = None) -> bool:
    del remote_ip
    if not captcha_required():
        return True
    if is_captcha_locked():
        return False
    if _verify_builtin(response):
        return True
    _record_failure()
    if not is_captcha_locked():
        new_captcha_question()
    return False


def verify_captcha_or_error(response: str, remote_ip: str | None = None) -> tuple[bool, str | None, str | None]:
    """Return (ok, error_message, fresh_question)."""
    del remote_ip
    if not captcha_required():
        return True, None, None
    if is_captcha_locked():
        return False, captcha_error_message(), None
    if _verify_builtin(response):
        return True, None, None
    _record_failure()
    question = None
    if not is_captcha_locked():
        question = new_captcha_question()
    return False, captcha_error_message(), question


def contact_needs_captcha(post_id: str) -> bool:
    if not captcha_required():
        return False
    revealed = session.get(CONTACT_REVEALS_KEY) or []
    if post_id in revealed:
        return False
    limit = int(current_app.config.get("CONTACT_SOFT_LIMIT", 5))
    return len(revealed) >= limit


def mark_contact_revealed(post_id: str) -> None:
    revealed = list(session.get(CONTACT_REVEALS_KEY) or [])
    if post_id not in revealed:
        revealed.append(post_id)
    session[CONTACT_REVEALS_KEY] = revealed[-200:]
    session.modified = True


def verify_turnstile(token: str, remote_ip: str | None = None) -> bool:
    return verify_captcha(token, remote_ip)


def extract_captcha_response() -> str:
    from flask import request

    return request.form.get("captcha_answer", "") or request.headers.get("X-Captcha-Answer", "")


def extract_captcha_token() -> str:
    return extract_captcha_response()
