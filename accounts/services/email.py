from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from accounts.tokens import email_verification_token


def _absolute_url(request, path: str) -> str:
    return request.build_absolute_uri(path)


def send_verification_email(request, user) -> None:
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = email_verification_token.make_token(user)
    path = reverse("accounts:verify_email", kwargs={"uidb64": uid, "token": token})
    context = {
        "user": user,
        "site_name": settings.SITE_NAME,
        "verify_url": _absolute_url(request, path),
    }
    subject = render_to_string("accounts/email/verify_email_subject.txt", context).strip()
    body = render_to_string("accounts/email/verify_email.txt", context)
    send_mail(
        subject,
        body,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )


def send_password_reset_email(request, user) -> None:
    """Optional helper for smoke tests; production uses Django PasswordResetView."""
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    path = reverse("accounts:password_reset_confirm", kwargs={"uidb64": uid, "token": token})
    context = {
        "user": user,
        "site_name": settings.SITE_NAME,
        "protocol": "https" if request.is_secure() else "http",
        "domain": request.get_host(),
        "uid": uid,
        "token": token,
        "reset_url": _absolute_url(request, path),
    }
    subject = render_to_string("accounts/email/password_reset_subject.txt", context).strip()
    body = render_to_string("accounts/email/password_reset_email.txt", context)
    send_mail(
        subject,
        body,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )
