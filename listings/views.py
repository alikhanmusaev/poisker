from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import F
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods, require_POST

from listings.constants import CATEGORY_LABELS, CITIES
from listings.forms import DraftPostForm, EditDraftPostForm, EditPostForm, PostForm
from listings.models import Post
from listings.services.posts import (
    ValidationError,
    create_post,
    delete_post,
    republish_post,
    submit_draft,
    sync_user_post_phones,
    unpublish_post,
    update_post,
)
from listings.services.show_context import build_show_context, increment_views
from listings.services.storage import upload_image


def _user_post_or_404(user, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.user_id != user.id and not user.is_staff:
        raise Http404
    return post


def _collect_images(request):
    image_keys = []
    for f in request.FILES.getlist("images")[:5]:
        if f:
            image_keys.append(upload_image(f))
    cover_index = int(request.POST.get("cover_index") or 0)
    if image_keys:
        cover_index = max(0, min(cover_index, len(image_keys) - 1))
    else:
        cover_index = 0
    return image_keys, cover_index


def _resolve_edit_images(request, post):
    """Return (image_keys, cover_index) or None if images were not changed."""
    existing = list(post.images or [])
    remove_raw = request.POST.getlist("remove_images")
    remove_idx = {int(x) for x in remove_raw if str(x).isdigit()}
    new_files = [f for f in request.FILES.getlist("images")[:5] if f]
    if not remove_idx and not new_files:
        return None

    kept = [url for i, url in enumerate(existing) if i not in remove_idx]
    new_keys = [upload_image(f) for f in new_files]
    images = (kept + new_keys)[:5]

    if new_keys:
        cover_new = int(request.POST.get("cover_index") or 0)
        cover_new = max(0, min(cover_new, len(new_keys) - 1))
        cover_index = len(kept) + cover_new
    else:
        old_cover = getattr(post, "cover_index", 0) or 0
        old_url = existing[old_cover] if existing and 0 <= old_cover < len(existing) else None
        if old_url and old_url in kept:
            cover_index = kept.index(old_url)
        else:
            cover_index = 0

    if images:
        cover_index = max(0, min(cover_index, len(images) - 1))
    else:
        cover_index = 0
    return images, cover_index


@login_required
@require_http_methods(["GET", "POST"])
def create(request):
    as_draft = request.POST.get("action") == "draft"
    form_class = DraftPostForm if as_draft else PostForm
    form = form_class(request.POST or None, request.FILES or None)
    errors = []
    if request.method == "POST" and form.is_valid():
        try:
            image_keys, cover_index = _collect_images(request)
            post = create_post(
                request.user,
                {
                    **form.cleaned_data,
                    "cover_index": cover_index,
                },
                image_keys=image_keys,
                as_draft=as_draft,
            )
            if as_draft:
                messages.success(request, "Черновик сохранён.")
                return redirect(f"{reverse('accounts:profile')}?tab=drafts")
            messages.success(request, "Объявление отправлено на модерацию.")
            return redirect("accounts:profile")
        except ValidationError as exc:
            errors.append(str(exc))
        except ValueError as exc:
            errors.append(str(exc))

    return render(
        request,
        "listings/create.html",
        {
            "form": form if request.method == "POST" else PostForm(),
            "errors": errors,
            "cities": CITIES,
        },
    )


@login_required
def my_posts(request):
    return redirect("accounts:profile")


@login_required
@require_http_methods(["GET", "POST"])
def edit(request, post_id):
    post = _user_post_or_404(request.user, post_id)
    if post.status == "hidden":
        messages.info(
            request,
            "Снятое объявление нельзя редактировать. Сначала опубликуйте его снова.",
        )
        return redirect(f"{reverse('accounts:profile')}?tab=hidden")
    if post.status not in ("draft", "pending", "published"):
        raise Http404

    as_draft = request.POST.get("action") == "draft"
    if as_draft and post.status != "draft":
        messages.error(request, "В черновик можно сохранить только черновик.")
        return redirect("listings:edit", post_id=post.pk)

    form_class = EditDraftPostForm if (as_draft or (request.method == "GET" and post.status == "draft")) else EditPostForm
    if request.method == "POST" and not as_draft:
        form_class = EditPostForm

    initial = {
        "title": post.title,
        "body": post.body,
        "category": post.category,
        "city": post.city,
        "price": post.price,
    }
    form = form_class(request.POST or None, request.FILES or None, initial=initial)
    errors = []
    if request.method == "POST" and form.is_valid():
        try:
            resolved = _resolve_edit_images(request, post)
            payload = {**form.cleaned_data}
            image_keys = None
            if resolved is not None:
                image_keys, cover_index = resolved
                payload["cover_index"] = cover_index
            update_post(post, request.user, payload, as_draft=as_draft, image_keys=image_keys)
            post.refresh_from_db()
            if as_draft:
                messages.success(request, "Черновик сохранён.")
                return redirect(f"{reverse('accounts:profile')}?tab=drafts")
            if post.status == "pending":
                messages.success(
                    request,
                    "Изменения сохранены. Объявление ждёт модерации.",
                )
            elif post.pending_revision:
                messages.success(
                    request,
                    "Изменения отправлены на модерацию. "
                    "Пока на сайте показывается прежняя версия.",
                )
            else:
                messages.success(request, "Изменения сохранены.")
            return redirect("accounts:profile")
        except ValidationError as exc:
            errors.append(str(exc))
        except ValueError as exc:
            errors.append(str(exc))
    return render(
        request,
        "listings/edit.html",
        {
            "form": form,
            "post": post,
            "errors": errors,
            "category_labels": CATEGORY_LABELS,
            "cities": CITIES,
            "is_draft": post.status == "draft",
            "awaits_moderation": post.status == "pending" or bool(post.pending_revision),
            "existing_image_count": len(post.images or []),
        },
    )


@login_required
@require_POST
def submit_for_moderation(request, post_id):
    post = _user_post_or_404(request.user, post_id)
    try:
        submit_draft(post, request.user)
        messages.success(request, "Объявление отправлено на модерацию.")
        return redirect("accounts:profile")
    except ValidationError as exc:
        messages.error(request, str(exc))
        return redirect("listings:edit", post_id=post.pk)


def _redirect_after_post_action(request, post):
    next_url = request.POST.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)
    if post.status in ("published", "pending", "hidden", "draft"):
        return redirect("listings:show", post_id=post.pk)
    return redirect("accounts:profile")


@login_required
@require_POST
def delete(request, post_id):
    post = _user_post_or_404(request.user, post_id)
    try:
        if post.status == "published":
            unpublish_post(post, request.user)
            messages.success(request, "Объявление снято с публикации.")
            next_url = request.POST.get("next")
            if not next_url:
                return redirect(f"{reverse('accounts:profile')}?tab=hidden")
        else:
            delete_post(post, request.user)
            messages.success(request, "Объявление удалено.")
            next_url = request.POST.get("next")
            if next_url and url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)
            return redirect("accounts:profile")
    except ValidationError as exc:
        messages.error(request, str(exc))
    return _redirect_after_post_action(request, post)


@login_required
@require_POST
def republish(request, post_id):
    post = _user_post_or_404(request.user, post_id)
    try:
        republish_post(post, request.user)
        messages.success(request, "Объявление отправлено на модерацию.")
        return redirect("accounts:profile")
    except ValidationError as exc:
        messages.error(request, str(exc))
    return _redirect_after_post_action(request, post)


def show(request, post_id):
    post = get_object_or_404(Post.objects.select_related("user"), pk=post_id)
    if post.status == "published" and post.expires_at and post.expires_at > timezone.now():
        from listings.services.seo_urls import post_public_url

        return redirect(post_public_url(post), permanent=True)
    if post.status not in ("published", "pending", "hidden", "draft", "expired"):
        raise Http404
    is_owner = post.user_id == getattr(request.user, "id", None)
    is_staff = bool(getattr(request.user, "is_staff", False) and request.user.is_authenticated)
    if post.status != "published" and not is_owner and not is_staff:
        raise Http404
    increment_views(post)
    return render(request, "listings/show.html", build_show_context(request, post))


@require_POST
def contact(request, post_id):
    if not request.user.is_authenticated:
        return JsonResponse(
            {
                "error": "Войдите или зарегистрируйтесь, чтобы увидеть телефон.",
                "login_required": True,
            },
            status=401,
        )
    from django.conf import settings

    from core.ratelimit import hit_rate_limit

    limit = getattr(settings, "CONTACT_RATE_LIMIT_PER_HOUR", 30)
    cache_key = f"contact-rate:{request.user.id}"
    if hit_rate_limit(cache_key, limit=limit, window_seconds=3600, fail_closed=True):
        return JsonResponse(
            {"error": "Слишком много запросов. Попробуйте позже."},
            status=429,
        )

    post = get_object_or_404(
        Post.objects.select_related("user"),
        pk=post_id,
        status="published",
    )
    phone = post.contact_phone or post.user.phone or ""
    if not phone:
        return JsonResponse({"error": "Телефон не указан"}, status=404)
    Post.objects.filter(pk=post.pk).update(contact_clicks=F("contact_clicks") + 1)
    if request.user.id != post.user_id:
        from reviews.services import record_phone_reveal

        record_phone_reveal(reviewer=request.user, post=post)
    return JsonResponse({"phone": phone})
