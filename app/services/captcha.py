import httpx
from flask import current_app


def verify_turnstile(token: str, remote_ip: str | None = None) -> bool:
    secret = current_app.config.get("TURNSTILE_SECRET_KEY", "")
    if not secret:
        if current_app.config.get("REQUIRE_TURNSTILE"):
            return False
        return True

    if not token:
        return False

    data = {"secret": secret, "response": token}
    if remote_ip:
        data["remoteip"] = remote_ip

    try:
        with httpx.Client(timeout=10) as client:
            resp = client.post(
                "https://challenges.cloudflare.com/turnstile/v0/siteverify",
                data=data,
            )
            result = resp.json()
            return bool(result.get("success"))
    except httpx.HTTPError:
        return False
