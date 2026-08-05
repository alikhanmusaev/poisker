import secrets

from django.conf import settings

# Inline styles are still used by templates. Inline scripts use a per-response
# nonce, so a markup injection cannot execute JavaScript by default.
_DEFAULT_CSP = (
    "default-src 'self'; "
    "script-src 'self' https://www.gstatic.com; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob:; "
    "font-src 'self'; "
    "connect-src 'self' https://firebaseinstallations.googleapis.com "
    "https://fcmregistrations.googleapis.com https://fcm.googleapis.com "
    "https://*.googleapis.com https://*.firebaseio.com; "
    "worker-src 'self'; "
    "object-src 'none'; "
    "base-uri 'self'; "
    # form-action also covers 302 targets after POST (Chrome). Allow T-Bank pay form.
    "form-action 'self' https://securepay.tinkoff.ru https://*.tinkoff.ru https://*.tbank.ru; "
    "frame-ancestors 'none'; "
    "upgrade-insecure-requests"
)
_DEFAULT_PERMISSIONS_POLICY = "camera=(), microphone=(), geolocation=(), payment=()"


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.csp_nonce = secrets.token_urlsafe(16)
        response = self.get_response(request)
        if getattr(settings, "SECURITY_HEADERS_ENABLED", True):
            response.headers.setdefault("X-Content-Type-Options", "nosniff")
            response.headers.setdefault("X-Frame-Options", "DENY")
            response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
            response.headers.setdefault("Permissions-Policy", _DEFAULT_PERMISSIONS_POLICY)
            response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
            csp = getattr(settings, "CONTENT_SECURITY_POLICY", "") or _DEFAULT_CSP
            csp = csp.replace("script-src 'self'", f"script-src 'self' 'nonce-{request.csp_nonce}'")
            if csp:
                response.headers.setdefault("Content-Security-Policy", csp)
        return response


class BlockedUserMiddleware:
    """Log out blocked users and reject their authenticated requests."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and getattr(user, "is_blocked", False):
            from django.contrib import messages
            from django.contrib.auth import logout
            from django.http import HttpResponseForbidden
            from django.shortcuts import redirect

            logout(request)
            if (
                request.headers.get("X-Requested-With") == "XMLHttpRequest"
                or request.path.endswith("/contact/")
            ):
                return HttpResponseForbidden("Аккаунт заблокирован.")
            messages.error(request, "Аккаунт заблокирован.")
            return redirect("accounts:login")
        return self.get_response(request)
