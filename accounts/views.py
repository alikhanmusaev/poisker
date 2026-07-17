from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LogoutView
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.encoding import force_str
from django.utils.http import url_has_allowed_host_and_scheme, urlsafe_base64_decode
from django.views.decorators.http import require_http_methods

from accounts.forms import LoginForm, ProfileForm, RegistrationForm, ResendVerificationForm
from accounts.models import User
from accounts.services.email import send_verification_email
from accounts.services.seller_stats import annotate_seller_posts, seller_stats_summary
from accounts.tokens import email_verification_token
from listings.constants import CATEGORY_LABELS, CITIES
from listings.models import Post
from listings.services.posts import sync_user_post_phones
from listings.services.search import remove_post_from_index

AUTH_BACKEND = "accounts.backends.EmailBackend"
PROFILE_URL = "accounts:profile"


def _user_posts_queryset(user):
    return annotate_seller_posts(
        Post.objects.filter(user=user).exclude(status="deleted")
    ).order_by("-created_at")


def _profile_return_url(tab: str = "active") -> str:
    url = reverse(PROFILE_URL)
    if tab in ("hidden", "drafts", "expired"):
        return f"{url}?tab={tab}"
    return url


def _delete_user_account(user) -> None:
    post_ids = list(user.posts.values_list("pk", flat=True))
    for post_id in post_ids:
        remove_post_from_index(str(post_id))
    user.delete()


def _decode_uid(uidb64: str):
    try:
        return force_str(urlsafe_base64_decode(uidb64))
    except (TypeError, ValueError, OverflowError):
        return None


@require_http_methods(["GET", "POST"])
def register(request):
    if request.user.is_authenticated:
        return redirect(PROFILE_URL)
    from django.conf import settings

    from core.http import get_client_ip
    from core.ratelimit import hit_rate_limit

    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        ip = get_client_ip(request) or "unknown"
        limit = getattr(settings, "AUTH_RATE_LIMIT_PER_HOUR", 30)
        if hit_rate_limit(
            f"auth-register:{ip}",
            limit=limit,
            window_seconds=3600,
            fail_closed=True,
        ):
            form.add_error(None, "Слишком много попыток. Попробуйте позже.")
        else:
            from django.utils import timezone

            user = form.save(commit=False)
            now = timezone.now()
            user.terms_accepted_at = now
            user.pdn_consent_at = now
            user.pdn_consent_version = getattr(settings, "PDN_CONSENT_VERSION", "")
            user.consent_ip = ip if ip != "unknown" else None
            user.save()
            try:
                send_verification_email(request, user)
            except Exception:
                messages.warning(
                    request,
                    "Аккаунт создан, но письмо не отправилось. Запросите подтверждение ещё раз.",
                )
            request.session["pending_verify_email"] = user.email
            return redirect("accounts:register_done")
    return render(request, "accounts/register.html", {"form": form})


@require_http_methods(["GET"])
def register_done(request):
    if request.user.is_authenticated:
        return redirect(PROFILE_URL)
    email = request.session.get("pending_verify_email") or ""
    return render(request, "accounts/register_done.html", {"email": email})


@require_http_methods(["GET"])
def verify_email(request, uidb64, token):
    uid = _decode_uid(uidb64)
    user = None
    if uid is not None:
        try:
            user = User.objects.get(pk=uid)
        except (User.DoesNotExist, ValueError, TypeError):
            user = None

    if user is None or not email_verification_token.check_token(user, token):
        messages.error(request, "Ссылка подтверждения недействительна или устарела.")
        return redirect("accounts:resend_verification")

    if not user.email_verified:
        user.email_verified = True
        user.save(update_fields=["email_verified"])

    request.session.pop("pending_verify_email", None)
    messages.success(request, "Email подтверждён. Теперь можно войти.")
    return redirect("accounts:login")


@require_http_methods(["GET", "POST"])
def resend_verification(request):
    if request.user.is_authenticated:
        return redirect(PROFILE_URL)
    from django.conf import settings

    from core.http import get_client_ip
    from core.ratelimit import hit_rate_limit

    initial = {}
    pending = request.session.get("pending_verify_email")
    if pending and request.method == "GET":
        initial["email"] = pending

    form = ResendVerificationForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        ip = get_client_ip(request) or "unknown"
        limit = getattr(settings, "AUTH_RATE_LIMIT_PER_HOUR", 30)
        if hit_rate_limit(
            f"auth-verify-resend:{ip}",
            limit=limit,
            window_seconds=3600,
            fail_closed=True,
        ):
            form.add_error(None, "Слишком много попыток. Попробуйте позже.")
        else:
            email = form.cleaned_data["email"]
            user = User.objects.filter(email__iexact=email).first()
            if user and not user.email_verified and not user.is_staff:
                try:
                    send_verification_email(request, user)
                except Exception:
                    form.add_error(None, "Не удалось отправить письмо. Попробуйте позже.")
                    return render(request, "accounts/resend_verification.html", {"form": form})
            request.session["pending_verify_email"] = email
            messages.success(
                request,
                "Если аккаунт с таким email ждёт подтверждения, мы отправили новое письмо.",
            )
            return redirect("accounts:register_done")
    return render(request, "accounts/resend_verification.html", {"form": form})


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect(PROFILE_URL)
    from django.conf import settings

    from core.http import get_client_ip
    from core.ratelimit import hit_rate_limit

    form = LoginForm(request, data=request.POST or None)
    if request.method == "POST":
        ip = get_client_ip(request) or "unknown"
        limit = getattr(settings, "AUTH_RATE_LIMIT_PER_HOUR", 30)
        if hit_rate_limit(
            f"auth-login:{ip}",
            limit=limit,
            window_seconds=3600,
            fail_closed=True,
        ):
            form.add_error(None, "Слишком много попыток входа. Попробуйте позже.")
        elif form.is_valid():
            login(request, form.get_user(), backend=AUTH_BACKEND)
            user = form.get_user()
            next_url = request.GET.get("next") or ""
            if user.is_staff:
                return redirect("moderation:dashboard")
            if next_url and url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)
            return redirect(PROFILE_URL)
        elif getattr(form, "unverified_email", None):
            request.session["pending_verify_email"] = form.unverified_email
    return render(request, "accounts/login.html", {"form": form})


class UserLogoutView(LogoutView):
    next_page = "core:index"


class RateLimitedPasswordResetView(auth_views.PasswordResetView):
    """Throttle password-reset POSTs per IP (fail-closed if cache is down)."""

    def post(self, request, *args, **kwargs):
        from django.conf import settings

        from core.http import get_client_ip
        from core.ratelimit import hit_rate_limit

        ip = get_client_ip(request) or "unknown"
        limit = getattr(settings, "AUTH_RATE_LIMIT_PER_HOUR", 30)
        if hit_rate_limit(
            f"auth-password-reset:{ip}",
            limit=limit,
            window_seconds=3600,
            fail_closed=True,
        ):
            form = self.get_form()
            form.add_error(None, "Слишком много попыток. Попробуйте позже.")
            return self.form_invalid(form)
        return super().post(request, *args, **kwargs)


@login_required
@require_http_methods(["GET"])
def profile(request):
    tab = request.GET.get("tab", "active")
    if tab not in ("active", "hidden", "drafts", "expired"):
        tab = "active"
    base = _user_posts_queryset(request.user)
    active_posts = base.exclude(status__in=("hidden", "draft", "expired"))
    hidden_posts = base.filter(status="hidden")
    draft_posts = base.filter(status="draft")
    expired_posts = base.filter(status="expired")
    return render(
        request,
        "accounts/profile.html",
        {
            "posts_tab": tab,
            "active_posts": active_posts,
            "hidden_posts": hidden_posts,
            "draft_posts": draft_posts,
            "expired_posts": expired_posts,
            "active_posts_count": active_posts.count(),
            "hidden_posts_count": hidden_posts.count(),
            "draft_posts_count": draft_posts.count(),
            "expired_posts_count": expired_posts.count(),
            "active_return_url": _profile_return_url("active"),
            "hidden_return_url": _profile_return_url("hidden"),
            "drafts_return_url": _profile_return_url("drafts"),
            "expired_return_url": _profile_return_url("expired"),
            "seller_stats": seller_stats_summary(request.user),
            "category_labels": CATEGORY_LABELS,
            "cities": CITIES,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def profile_edit(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        sync_user_post_phones(request.user)
        messages.success(request, "Личные данные сохранены.")
        return redirect(PROFILE_URL)
    return render(request, "accounts/profile_edit.html", {"form": form})


@login_required
@require_http_methods(["GET", "POST"])
def profile_delete(request):
    if request.user.is_superuser:
        messages.error(request, "Аккаунт администратора нельзя удалить здесь.")
        return redirect("accounts:profile_edit")

    if request.method == "POST":
        user = request.user
        logout(request)
        _delete_user_account(user)
        messages.success(request, "Профиль удалён.")
        return redirect("core:index")

    posts_count = request.user.posts.exclude(status="deleted").count()
    return render(
        request,
        "accounts/profile_delete.html",
        {"posts_count": posts_count},
    )
