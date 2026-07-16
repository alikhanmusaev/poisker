from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_POST

from bookmarks.models import CategoryBookmark, Notification, PostBookmark
from bookmarks.services import (
    delete_all_notifications,
    delete_notification,
    is_category_bookmarked,
    mark_all_notifications_read,
    mark_notification_read,
    toggle_category_bookmark,
    toggle_post_bookmark,
)
from listings.constants import CATEGORIES, CATEGORY_ICONS, CATEGORY_LABELS, CITIES
from listings.models import Post


def _category_url(category: str) -> str:
    return f"/{category}/"


def _safe_next(request, fallback: str) -> str:
    candidate = request.POST.get("next") or request.GET.get("next") or ""
    if candidate and url_has_allowed_host_and_scheme(candidate, allowed_hosts={request.get_host()}):
        return candidate
    return fallback


@login_required
@require_GET
def index(request):
    tab = request.GET.get("tab", "posts")
    if tab not in ("posts", "categories"):
        tab = "posts"

    post_bookmarks = (
        PostBookmark.objects.filter(user=request.user)
        .select_related("post", "post__user")
        .order_by("-created_at")
    )
    category_bookmarks = (
        CategoryBookmark.objects.filter(user=request.user).order_by("-created_at")
    )
    category_rows = [
        {
            "slug": bookmark.category,
            "label": CATEGORY_LABELS.get(bookmark.category, bookmark.category),
            "icon": CATEGORY_ICONS.get(bookmark.category, "layout-grid"),
            "url": _category_url(bookmark.category),
            "created_at": bookmark.created_at,
        }
        for bookmark in category_bookmarks
        if bookmark.category in CATEGORIES
    ]

    return render(
        request,
        "bookmarks/index.html",
        {
            "tab": tab,
            "post_bookmarks": post_bookmarks,
            "category_rows": category_rows,
            "all_categories": [
                {
                    "slug": slug,
                    "label": label,
                    "icon": icon,
                    "bookmarked": is_category_bookmarked(request.user, slug),
                    "url": _category_url(slug),
                }
                for slug, (label, icon) in CATEGORIES.items()
            ],
            "cities": CITIES,
            "category_labels": CATEGORY_LABELS,
        },
    )


@login_required
@require_POST
def toggle_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    bookmarked = toggle_post_bookmark(request.user, post)
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"ok": True, "bookmarked": bookmarked})
    next_url = _safe_next(request, reverse("bookmarks:index"))
    if bookmarked:
        messages.success(request, "Объявление добавлено в закладки.")
    else:
        messages.success(request, "Объявление убрано из закладок.")
    return redirect(next_url)


@login_required
@require_POST
def toggle_category(request, category):
    if category not in CATEGORIES:
        raise Http404
    try:
        bookmarked = toggle_category_bookmark(request.user, category)
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect("bookmarks:index")
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"ok": True, "bookmarked": bookmarked})
    next_url = _safe_next(request, reverse("bookmarks:index") + "?tab=categories")
    label = CATEGORY_LABELS.get(category, category)
    if bookmarked:
        messages.success(request, f"Категория «{label}» добавлена в закладки.")
    else:
        messages.success(request, f"Категория «{label}» убрана из закладок.")
    return redirect(next_url)


@login_required
@require_GET
def notifications(request):
    items = (
        Notification.objects.filter(user=request.user)
        .select_related("post")
        .order_by("-created_at")[:100]
    )
    return render(
        request,
        "bookmarks/notifications.html",
        {
            "notifications": items,
            "category_labels": CATEGORY_LABELS,
            "cities": CITIES,
        },
    )


@login_required
@require_POST
def mark_read(request, notification_id):
    notification = get_object_or_404(Notification, pk=notification_id, user=request.user)
    mark_notification_read(notification, request.user)
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"ok": True})
    if notification.kind in (
        Notification.KIND_NEW_REVIEW,
        Notification.KIND_REVIEW_REPLY,
    ):
        seller_id = (notification.payload or {}).get("seller_id")
        review_id = (notification.payload or {}).get("review_id")
        if seller_id:
            url = reverse("reviews:seller_profile", args=[seller_id])
            if review_id:
                url = f"{url}#review-{review_id}"
            return redirect(url)
    if notification.post_id and notification.post and notification.post.status == "published":
        return redirect(notification.post.get_absolute_url())
    if notification.category and notification.category in CATEGORIES:
        return redirect(_category_url(notification.category))
    return redirect("bookmarks:notifications")


@login_required
@require_POST
def mark_all_read(request):
    mark_all_notifications_read(request.user)
    messages.success(request, "Все уведомления прочитаны.")
    return redirect("bookmarks:notifications")


@login_required
@require_POST
def delete_notification_view(request, notification_id):
    notification = get_object_or_404(Notification, pk=notification_id, user=request.user)
    delete_notification(notification, request.user)
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"ok": True})
    messages.success(request, "Уведомление удалено.")
    return redirect("bookmarks:notifications")


@login_required
@require_POST
def delete_all_notifications_view(request):
    count = delete_all_notifications(request.user)
    if count:
        messages.success(request, "Все уведомления удалены.")
    return redirect("bookmarks:notifications")
