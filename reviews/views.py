from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from accounts.models import User
from listings.models import Post
from reviews.forms import SellerReviewForm, SellerReviewReplyForm
from reviews.services import (
    ReviewError,
    can_review_seller,
    get_review,
    phone_review_unlock_at,
    reply_to_review,
    review_denied_message,
    seller_reviews_qs,
    upsert_review,
)


def seller_profile(request, user_id):
    seller = get_object_or_404(User, pk=user_id, is_blocked=False)
    live_posts = Post.objects.filter(
        user=seller,
        status="published",
        expires_at__gte=timezone.now(),
    )
    posts = list(live_posts.order_by("-rank_score", "-created_at")[:12])
    reviews = list(seller_reviews_qs(seller)[:50])
    existing = get_review(request.user, seller) if request.user.is_authenticated else None
    can_review = (
        can_review_seller(request.user, seller) if request.user.is_authenticated else False
    )
    unlock_at = None
    if request.user.is_authenticated and not can_review:
        unlock_at = phone_review_unlock_at(request.user, seller)
        if unlock_at and unlock_at <= timezone.now():
            unlock_at = None
    is_owner = request.user.is_authenticated and request.user.id == seller.id
    return render(
        request,
        "reviews/seller_profile.html",
        {
            "seller": seller,
            "reviews": reviews,
            "posts": posts,
            "posts_total": live_posts.count(),
            "can_review": can_review,
            "existing_review": existing,
            "phone_review_unlock_at": unlock_at,
            "is_seller_owner": is_owner,
            "page_title": seller.display_name,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def review_seller(request, user_id):
    seller = get_object_or_404(User, pk=user_id, is_blocked=False)
    if not can_review_seller(request.user, seller):
        messages.error(request, review_denied_message(request.user, seller))
        return redirect("reviews:seller_profile", user_id=seller.id)

    existing = get_review(request.user, seller)
    if request.method == "POST":
        form = SellerReviewForm(request.POST, instance=existing)
        if form.is_valid():
            try:
                upsert_review(
                    reviewer=request.user,
                    seller=seller,
                    rating=form.cleaned_data["rating"],
                    comment=form.cleaned_data.get("comment") or "",
                )
                messages.success(request, "Отзыв сохранён.")
                return redirect("reviews:seller_profile", user_id=seller.id)
            except ReviewError as exc:
                messages.error(request, str(exc))
    else:
        form = SellerReviewForm(instance=existing)

    return render(
        request,
        "reviews/review_form.html",
        {
            "seller": seller,
            "form": form,
            "existing_review": existing,
            "page_title": f"Отзыв о {seller.display_name}",
        },
    )


@login_required
@require_POST
def reply_review(request, user_id, review_id):
    seller = get_object_or_404(User, pk=user_id, is_blocked=False)
    if request.user.id != seller.id:
        messages.error(request, "Отвечать может только владелец профиля.")
        return redirect("reviews:seller_profile", user_id=seller.id)

    form = SellerReviewReplyForm(request.POST)
    if form.is_valid():
        try:
            review = reply_to_review(
                seller=request.user,
                review_id=review_id,
                text=form.cleaned_data["reply_text"],
            )
            messages.success(request, "Ответ опубликован.")
            url = reverse("reviews:seller_profile", args=[seller.id])
            return redirect(f"{url}#review-{review.id}")
        except ReviewError as exc:
            messages.error(request, str(exc))
    else:
        err = form.errors.get("reply_text")
        messages.error(request, err[0] if err else "Проверьте текст ответа.")
    return redirect("reviews:seller_profile", user_id=seller.id)
