from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse


# Staff (moderators) work in /moderation/; seller product surfaces are blocked.
_SELLER_EXACT = {
    "/posts/new/",
    "/posts/my/",
    "/accounts/profile/",
    "/accounts/profile/edit/",
    "/accounts/profile/delete/",
    "/accounts/password-change/",
    "/accounts/password-change/done/",
    "/bookmarks/",
    "/notifications/",
    "/messages/",
}

_SELLER_PREFIXES = (
    "/messages/",
    "/bookmarks/",
    "/notifications/",
)

_SELLER_POST_SUFFIXES = (
    "/edit/",
    "/delete/",
    "/republish/",
    "/submit/",
    "/contact/",
    "/report/",
)


def _is_seller_route(path: str) -> bool:
    if path in _SELLER_EXACT:
        return True
    if any(path.startswith(prefix) for prefix in _SELLER_PREFIXES):
        return True
    if path.startswith("/posts/") and path != "/posts/new/":
        return any(path.endswith(suf) for suf in _SELLER_POST_SUFFIXES)
    if path.startswith("/accounts/profile"):
        return True
    return False


class ModeratorSellerIsolationMiddleware:
    """Redirect staff away from seller features (create listing, messaging, etc.)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if (
            user is not None
            and user.is_authenticated
            and getattr(user, "is_staff", False)
            and not request.path.startswith("/moderation/")
            and not request.path.startswith("/admin/")
            and not request.path.startswith("/accounts/logout")
            and not request.path.startswith("/accounts/login")
            and not request.path.startswith("/static/")
            and not request.path.startswith("/media/")
            and _is_seller_route(request.path)
        ):
            messages.info(request, "Раздел для продавцов недоступен модераторам.")
            return redirect(reverse("moderation:dashboard"))
        return self.get_response(request)
