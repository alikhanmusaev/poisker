from concurrent.futures import ThreadPoolExecutor

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import F
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods, require_POST
import json
import logging

from listings.constants import CATEGORY_LABELS, CITIES
from listings.forms import DraftPostForm, EditDraftPostForm, EditPostForm, PostForm
from listings.models import Post
from listings.services.posts import (
    ValidationError,
    can_edit_rejected_post,
    create_post,
    delete_post,
    republish_post,
    mark_post_sold,
    submit_draft,
    sync_user_post_phones,
    unpublish_post,
    update_post,
)
from listings.services.promote import (
    FAILED_STATUSES,
    PAID_STATUSES,
    PromoteError,
    apply_paid_promotion,
    find_promotion_for_notification,
    has_pending_promotion,
    mark_promotion_failed,
    start_promotion,
    sync_promotion_after_return,
)
from listings.services.show_context import build_show_context, increment_views
from listings.services.storage import upload_image, uploaded_sha256
from listings.services.tbank import verify_notification

logger = logging.getLogger(__name__)


def _user_post_or_404(user, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.user_id != user.id and not user.is_staff:
        raise Http404
    return post


def _upload_images(files):
    """Upload up to 5 images; parallelize when more than one file."""
    items = [f for f in files if f][:5]
    if not items:
        return []
    if len(items) == 1:
        return [upload_image(items[0])]
    workers = min(len(items), 3)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(upload_image, items))


def _collect_images(request):
    files = request.FILES.getlist("images")[:5]
    image_hashes = [uploaded_sha256(image) for image in files if image]
    image_keys = _upload_images(files)
    cover_index = int(request.POST.get("cover_index") or 0)
    if image_keys:
        cover_index = max(0, min(cover_index, len(image_keys) - 1))
    else:
        cover_index = 0
    return image_keys, cover_index, image_hashes


def _resolve_edit_images(request, post):
    """Return (image_keys, cover_index) or None if images were not changed."""
    existing = list(post.images or [])
    remove_raw = request.POST.getlist("remove_images")
    remove_idx = {int(x) for x in remove_raw if str(x).isdigit()}
    new_files = [f for f in request.FILES.getlist("images")[:5] if f]
    if not remove_idx and not new_files:
        return None

    kept = [url for i, url in enumerate(existing) if i not in remove_idx]
    new_keys = _upload_images(new_files)
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
    preferred_settlement = getattr(request.user, "preferred_settlement", None)
    initial = (
        {
            "settlement_id": preferred_settlement.id,
            "city": preferred_settlement.slug,
        }
        if preferred_settlement is not None
        else None
    )
    form = form_class(request.POST or None, request.FILES or None, initial=initial)
    errors = []
    if request.method == "POST" and form.is_valid():
        try:
            if not as_draft:
                from core.ratelimit import hit_rate_limit
                from django.conf import settings

                if hit_rate_limit(
                    f"post-create:{request.user.pk}",
                    limit=settings.POST_CREATE_RATE_LIMIT_PER_DAY,
                    window_seconds=24 * 60 * 60,
                    fail_closed=True,
                ):
                    raise ValidationError("Лимит публикаций на сегодня исчерпан. Попробуйте завтра.")
            image_keys, cover_index, image_hashes = _collect_images(request)
            post = create_post(
                request.user,
                {
                    **form.cleaned_data,
                    "cover_index": cover_index,
                },
                image_keys=image_keys,
                image_hashes=image_hashes,
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
            "form": form if request.method == "POST" else PostForm(initial=initial),
            "errors": errors,
            "cities": CITIES,
            "settlement_name": preferred_settlement.display_name if preferred_settlement else "",
        },
    )


@login_required
def my_posts(request):
    return redirect("accounts:profile")


@login_required
@require_http_methods(["GET", "POST"])
def edit(request, post_id):
    post = get_object_or_404(Post.objects.select_related("settlement__region"), pk=post_id)
    if post.user_id != request.user.id and not request.user.is_staff:
        raise Http404
    if post.status == "sold":
        messages.info(request, "Проданное объявление нельзя редактировать.")
        return redirect("accounts:profile")
    if post.status == "hidden" and not can_edit_rejected_post(post):
        messages.info(
            request,
            "Снятое объявление нельзя редактировать. Сначала опубликуйте его снова.",
        )
        return redirect(f"{reverse('accounts:profile')}?tab=hidden")
    if post.status not in ("draft", "pending", "published", "hidden"):
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
        "settlement_id": post.settlement_id,
        "condition": post.condition,
        "price": post.price,
    }
    form = form_class(request.POST or None, request.FILES or None, initial=initial)
    errors = []
    if request.method == "POST" and form.is_valid():
        try:
            was_rejected = can_edit_rejected_post(post)
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
                if was_rejected:
                    messages.success(
                        request,
                        "Изменения сохранены. Объявление снова отправлено на модерацию.",
                    )
                else:
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
            "settlement_name": post.settlement.display_name if post.settlement else "",
            "is_draft": post.status == "draft",
            "awaits_moderation": post.status == "pending" or bool(post.pending_revision),
            "is_rejected": can_edit_rejected_post(post),
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


@login_required
@require_POST
def mark_sold(request, post_id):
    post = _user_post_or_404(request.user, post_id)
    try:
        mark_post_sold(post, request.user)
        messages.success(request, "Объявление отмечено как проданное и снято из поиска.")
    except ValidationError as exc:
        messages.error(request, str(exc))
    return redirect("accounts:profile")


def show(request, post_id):
    post = get_object_or_404(Post.objects.select_related("user"), pk=post_id)
    if post.status == "published" and post.expires_at and post.expires_at > timezone.now():
        from listings.services.seo_urls import post_public_url

        return redirect(post_public_url(post), permanent=True)
    if post.status not in ("published", "pending", "hidden", "sold", "draft", "expired"):
        raise Http404
    is_owner = post.user_id == getattr(request.user, "id", None)
    is_staff = bool(getattr(request.user, "is_staff", False) and request.user.is_authenticated)
    if post.status != "published" and not is_owner and not is_staff:
        raise Http404
    if is_owner and has_pending_promotion(post) and not post.is_promoted:
        outcome = sync_promotion_after_return(post)
        post.refresh_from_db()
        if outcome == "promoted" and post.is_promoted and post.paid_until:
            until = timezone.localtime(post.paid_until).strftime("%d.%m.%Y %H:%M")
            messages.success(
                request,
                f"Объявление поднято. Оно выше в поиске до {until}.",
            )
            from listings.services.seo_urls import post_public_url

            return redirect(post_public_url(post))
    increment_views(request, post)
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


@login_required
@require_POST
def promote(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    try:
        payment_url = start_promotion(
            post,
            user=request.user,
            absolute_uri=request.build_absolute_uri,
        )
    except PromoteError as exc:
        messages.error(request, str(exc))
        from listings.services.seo_urls import post_public_url

        return redirect(post_public_url(post) if post.status == "published" else "accounts:profile")
    return redirect(payment_url)


@login_required
@require_GET
def promote_status(request, post_id):
    """Return the bank-verified promotion state without navigating the page."""
    post = _user_post_or_404(request.user, post_id)
    if post.status != "published":
        raise Http404
    if has_pending_promotion(post) and not post.is_promoted:
        sync_promotion_after_return(post)
        post.refresh_from_db()
    if post.is_promoted:
        return JsonResponse({"status": "promoted"})
    return JsonResponse({"status": "pending" if has_pending_promotion(post) else "unknown"})


@login_required
def promote_success(request, post_id):
    post = get_object_or_404(Post, pk=post_id, user=request.user)
    from listings.services.seo_urls import post_public_url

    outcome = sync_promotion_after_return(post)
    post.refresh_from_db()
    redirect_url = post_public_url(post)

    if outcome == "promoted" and post.is_promoted and post.paid_until:
        until = timezone.localtime(post.paid_until).strftime("%d.%m.%Y %H:%M")
        messages.success(
            request,
            f"Объявление поднято. Оно выше в поиске до {until}.",
        )
        return redirect(redirect_url)

    if outcome == "failed":
        messages.error(
            request,
            "Оплата не подтверждена. Объявление не поднято — можно попробовать снова.",
        )
        return redirect(redirect_url)

    messages.warning(
        request,
        "Платёж получен. Ждём подтверждение банка — обычно до минуты. "
        "Статус обновится на этой странице автоматически.",
    )
    return redirect(f"{redirect_url}?promote=pending")


@login_required
def promote_fail(request, post_id):
    post = get_object_or_404(Post, pk=post_id, user=request.user)
    messages.error(
        request,
        "Оплата не завершена. Объявление не поднято — можно попробовать снова.",
    )
    from listings.services.seo_urls import post_public_url

    return redirect(post_public_url(post) if post.status == "published" else "accounts:profile")


@csrf_exempt
@require_POST
def tbank_notify(request):
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError):
        return HttpResponse("bad request", status=400)

    if not verify_notification(payload):
        logger.warning("T-Bank notify: invalid token")
        return HttpResponse("invalid token", status=403)

    status = str(payload.get("Status") or "")
    order_id = str(payload.get("OrderId") or "")
    payment_id = str(payload.get("PaymentId") or "")
    promo = find_promotion_for_notification(order_id=order_id, payment_id=payment_id)
    if promo is None:
        logger.warning("T-Bank notify: promotion not found order=%s payment=%s", order_id, payment_id)
        return HttpResponse("OK")

    if status in PAID_STATUSES:
        try:
            apply_paid_promotion(promo)
        except Exception:
            logger.exception("T-Bank notify: apply failed for promo=%s", promo.pk)
            return HttpResponse("error", status=500)
    elif status in FAILED_STATUSES:
        mark_promotion_failed(promo)

    return HttpResponse("OK")
