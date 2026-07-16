from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from listings.constants import CATEGORY_LABELS, CITIES, MODERATION_REJECT_REASONS, REPORT_REASONS, REPORT_STATUS_LABELS
from listings.models import Post, Report
from listings.services.posts import ValidationError
from listings.utils.post_display import ordered_images
from moderation.decorators import staff_required
from moderation.services import (
    approve_post,
    hide_post,
    hidden_queue,
    mark_post_reports_reviewed,
    mark_report_reviewed,
    moderation_counts,
    pending_queue,
    reject_post,
    reports_queue,
    resolve_reports_and_hide,
    revisions_queue,
)

PER_PAGE = 20


def _counts_context():
    return {"mod_counts": moderation_counts()}


@staff_required
@require_GET
def dashboard(request):
    counts = moderation_counts()
    return render(
        request,
        "moderation/dashboard.html",
        {
            **_counts_context(),
            "active_nav": "dashboard",
            "page_title": "Обзор",
            "pending_preview": pending_queue()[:5],
            "revision_preview": revisions_queue()[:5],
            "report_preview": reports_queue(status="new")[:5],
            "counts": counts,
            "category_labels": CATEGORY_LABELS,
            "cities": CITIES,
            "report_reasons": REPORT_REASONS,
        },
    )


@staff_required
@require_GET
def queue(request):
    tab = request.GET.get("tab", "pending")
    if tab not in ("pending", "revisions", "hidden"):
        tab = "pending"
    if tab == "pending":
        qs = pending_queue()
    elif tab == "revisions":
        qs = revisions_queue()
    else:
        qs = hidden_queue()
    page_obj = Paginator(qs, PER_PAGE).get_page(request.GET.get("page"))
    return render(
        request,
        "moderation/queue.html",
        {
            **_counts_context(),
            "active_nav": "queue",
            "page_title": "Очередь модерации",
            "tab": tab,
            "page_obj": page_obj,
            "category_labels": CATEGORY_LABELS,
            "cities": CITIES,
        },
    )


@staff_required
@require_GET
def reports(request):
    status = request.GET.get("status", "new")
    if status not in ("new", "reviewed", "all"):
        status = "new"
    qs = reports_queue(status=None if status == "all" else status)
    page_obj = Paginator(qs, PER_PAGE).get_page(request.GET.get("page"))
    return render(
        request,
        "moderation/reports.html",
        {
            **_counts_context(),
            "active_nav": "reports",
            "page_title": "Жалобы",
            "status_filter": status,
            "page_obj": page_obj,
            "report_reasons": REPORT_REASONS,
            "report_status_labels": REPORT_STATUS_LABELS,
            "category_labels": CATEGORY_LABELS,
            "cities": CITIES,
        },
    )


@staff_required
@require_GET
def post_detail(request, post_id):
    post = get_object_or_404(Post.objects.select_related("user"), pk=post_id)
    open_reports = (
        Report.objects.filter(post=post, status="new")
        .select_related("reporter")
        .order_by("-created_at")
    )
    return render(
        request,
        "moderation/post_detail.html",
        {
            **_counts_context(),
            "active_nav": "queue",
            "page_title": post.title,
            "post": post,
            "images": ordered_images(post),
            "open_reports": open_reports,
            "revision": post.pending_revision or {},
            "category_labels": CATEGORY_LABELS,
            "cities": CITIES,
            "report_reasons": REPORT_REASONS,
            "reject_reasons": MODERATION_REJECT_REASONS,
        },
    )


def _redirect_back(request, fallback: str):
    nxt = request.POST.get("next") or request.GET.get("next")
    if nxt and nxt.startswith("/") and not nxt.startswith("//"):
        return redirect(nxt)
    return redirect(fallback)


@staff_required
@require_POST
def approve(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    try:
        approve_post(post, request.user)
        messages.success(request, "Объявление опубликовано.")
    except ValidationError as exc:
        messages.error(request, str(exc))
    return _redirect_back(request, reverse("moderation:queue"))


@staff_required
@require_POST
def reject(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    try:
        had_revision = bool(post.pending_revision) and post.status == "published"
        reject_post(post, request.user, reason=request.POST.get("reason", ""))
        if had_revision:
            messages.success(request, "Правки отклонены, объявление осталось опубликованным.")
        else:
            messages.success(request, "Объявление отклонено и скрыто.")
    except ValidationError as exc:
        messages.error(request, str(exc))
        return _redirect_back(request, reverse("moderation:post_detail", args=[post.pk]))
    return _redirect_back(request, reverse("moderation:queue"))


@staff_required
@require_POST
def hide(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    try:
        hide_post(post, request.user, reason=request.POST.get("reason", ""))
        messages.success(request, "Объявление скрыто.")
    except ValidationError as exc:
        messages.error(request, str(exc))
        return _redirect_back(request, reverse("moderation:post_detail", args=[post.pk]))
    return _redirect_back(request, reverse("moderation:post_detail", args=[post.pk]))


@staff_required
@require_POST
def report_review(request, report_id):
    report = get_object_or_404(Report, pk=report_id)
    try:
        mark_report_reviewed(report, request.user)
        messages.success(request, "Жалоба отмечена как рассмотренная.")
    except ValidationError as exc:
        messages.error(request, str(exc))
    return _redirect_back(request, reverse("moderation:reports"))


@staff_required
@require_POST
def post_resolve_reports(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    action = request.POST.get("action", "keep")
    try:
        if action == "hide":
            resolve_reports_and_hide(
                post,
                request.user,
                reason=request.POST.get("reason", "") or "Скрыто по жалобам пользователей.",
            )
            messages.success(request, "Жалобы рассмотрены, объявление скрыто.")
        else:
            count = mark_post_reports_reviewed(post, request.user)
            messages.success(request, f"Отмечено жалоб: {count}. Объявление оставлено.")
    except ValidationError as exc:
        messages.error(request, str(exc))
    return _redirect_back(request, reverse("moderation:post_detail", args=[post.pk]))
