from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from core.http import get_client_ip
from listings.constants import CATEGORY_LABELS, CITIES
from listings.forms import ReportForm
from listings.models import Post, Report
from listings.services.ranking import maybe_auto_hide
from listings.services.seo_urls import post_public_url
from listings.services.storage import (
    canonical_media_key,
    ensure_variant_exists,
    generate_presigned_get_url,
    get_object_bytes,
)


def _media_url(key: str) -> str:
    return f"/media/{key}"


def _posts_with_key(key: str):
    """Exact JSON membership lookup — variants resolve to the stored full JPEG URL."""
    media_url = _media_url(canonical_media_key(key))
    return list(Post.objects.filter(images__contains=[media_url]).only(
        "id", "status", "expires_at", "user_id", "images"
    ))


def serve_media(request, key: str):
    if ".." in key or key.startswith("/"):
        raise Http404
    if key.startswith("posts/"):
        allowed = False
        is_public = False
        for post in _posts_with_key(key):
            if post.status == "published" and post.expires_at > timezone.now():
                allowed = True
                is_public = True
                break
            if request.user.is_authenticated and post.user_id == request.user.id:
                allowed = True
                break
            if request.user.is_staff:
                allowed = True
                break
        if not allowed:
            raise Http404
        # Prefer direct GET (no HEAD round-trip). Materialize only on miss.
        try:
            data, content_type = get_object_bytes(key)
        except Exception:
            try:
                ensure_variant_exists(key)
                data, content_type = get_object_bytes(key)
            except Exception as exc:
                raise Http404 from exc
        if is_public:
            signed = generate_presigned_get_url(key, expires=900)
            if signed:
                return HttpResponseRedirect(signed)
        # UUID filenames are content-addressed — long cache helps repeat views / Lighthouse reruns.
        return HttpResponse(
            data,
            content_type=content_type,
            headers={"Cache-Control": "public, max-age=31536000, immutable"},
        )
    elif key.startswith("messages/"):
        if not request.user.is_authenticated:
            raise Http404
        from messaging.models import Message

        image_url = _media_url(canonical_media_key(key))
        allowed = Message.objects.filter(image=image_url).filter(
            Q(conversation__buyer=request.user) | Q(conversation__seller=request.user)
        ).exists()
        if not allowed and not request.user.is_staff:
            raise Http404
        try:
            data, content_type = get_object_bytes(key)
        except Exception:
            try:
                ensure_variant_exists(key)
                data, content_type = get_object_bytes(key)
            except Exception as exc:
                raise Http404 from exc
        return HttpResponse(
            data,
            content_type=content_type,
            headers={"Cache-Control": "private, max-age=300"},
        )
    raise Http404


@login_required
@require_http_methods(["GET", "POST"])
def report_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = ReportForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        reporter = request.user
        ip = get_client_ip(request)
        if Report.objects.filter(post=post, reporter=reporter).exists() or (
            ip and Report.objects.filter(post=post, reporter_ip=ip).exists()
        ):
            form.add_error(None, "Вы уже отправляли жалобу на это объявление.")
        else:
            Report.objects.create(
                post=post,
                reason=form.cleaned_data["reason"],
                comment=form.cleaned_data.get("comment") or "",
                reporter_ip=ip,
                reporter=reporter,
            )
            post.reports_count += 1
            post.save(update_fields=["reports_count"])
            maybe_auto_hide(post)
            return redirect(post_public_url(post))
    return render(
        request,
        "listings/report.html",
        {"form": form, "post": post, "category_labels": CATEGORY_LABELS, "cities": CITIES},
    )
