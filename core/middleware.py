from django.conf import settings

# 'unsafe-inline' for styles/scripts: templates use a few inline styles and one
# small admin bootstrap script; tighten later if those move to static files.
_DEFAULT_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob:; "
    "font-src 'self'; "
    "connect-src 'self'; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'none'; "
    "upgrade-insecure-requests"
)
_DEFAULT_PERMISSIONS_POLICY = "camera=(), microphone=(), geolocation=(), payment=()"


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if getattr(settings, "SECURITY_HEADERS_ENABLED", True):
            response.headers.setdefault("X-Content-Type-Options", "nosniff")
            response.headers.setdefault("X-Frame-Options", "DENY")
            response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
            response.headers.setdefault("Permissions-Policy", _DEFAULT_PERMISSIONS_POLICY)
            response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
            csp = getattr(settings, "CONTENT_SECURITY_POLICY", "") or _DEFAULT_CSP
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
