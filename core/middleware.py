from django.conf import settings


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if getattr(settings, "SECURITY_HEADERS_ENABLED", True):
            response.headers.setdefault("X-Content-Type-Options", "nosniff")
            response.headers.setdefault("X-Frame-Options", "DENY")
            response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
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
