from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from listings.constants import CATEGORY_LABELS, CITIES
from listings.models import Post
from listings.services.storage import upload_image
from messaging.forms import MessageForm
from messaging.services import (
    MessagingError,
    ensure_can_message_post,
    find_active_conversation,
    get_conversation_for_user,
    get_or_create_conversation,
    hide_conversation,
    inbox_conversations,
    mark_conversation_read,
    send_message,
)


@login_required
def inbox(request):
    conversations = inbox_conversations(request.user)
    return render(
        request,
        "messaging/inbox.html",
        {
            "conversations": conversations,
            "cities": CITIES,
            "category_labels": CATEGORY_LABELS,
        },
    )


@login_required
@require_http_methods(["POST"])
def delete_conversation(request, conversation_id):
    try:
        conversation = get_conversation_for_user(request.user, conversation_id)
        hide_conversation(conversation, request.user)
    except MessagingError as exc:
        raise Http404 from exc
    messages.success(request, "Чат удалён.")
    return redirect("messaging:inbox")


@login_required
@require_http_methods(["GET", "POST"])
def thread(request, conversation_id):
    try:
        conversation = get_conversation_for_user(request.user, conversation_id)
    except MessagingError as exc:
        raise Http404 from exc

    form = MessageForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        from django.conf import settings

        from core.ratelimit import hit_rate_limit

        limit = getattr(settings, "MESSAGING_RATE_LIMIT_PER_HOUR", 60)
        if hit_rate_limit(
            f"msg-rate:{request.user.id}",
            limit=limit,
            window_seconds=3600,
            fail_closed=True,
        ):
            messages.error(request, "Слишком много сообщений. Попробуйте позже.")
        else:
            image_url = ""
            image_file = form.cleaned_data.get("image")
            if image_file:
                try:
                    image_url = upload_image(image_file, prefix="messages")
                except ValueError as exc:
                    form.add_error("image", str(exc))
            if not form.errors:
                try:
                    send_message(
                        conversation,
                        request.user,
                        form.cleaned_data["body"],
                        image=image_url,
                    )
                    return redirect("messaging:thread", conversation_id=conversation.pk)
                except MessagingError as exc:
                    messages.error(request, str(exc))

    mark_conversation_read(conversation, request.user)
    message_list = (
        conversation.messages.select_related("sender")
        .exclude(body="", image="")
        .order_by("created_at")
    )
    other_user = conversation.other_participant(request.user)
    can_leave_review = False
    existing_seller_review = None
    if request.user.id == conversation.buyer_id:
        from reviews.services import can_review_seller, get_review

        can_leave_review = can_review_seller(request.user, other_user)
        existing_seller_review = get_review(request.user, other_user)

    return render(
        request,
        "messaging/thread.html",
        {
            "conversation": conversation,
            "post": conversation.post,
            "other_user": other_user,
            "thread_messages": message_list,
            "form": form if form.errors else MessageForm(),
            "cities": CITIES,
            "category_labels": CATEGORY_LABELS,
            "can_review_seller": can_leave_review,
            "existing_seller_review": existing_seller_review,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def start(request, post_id):
    post = get_object_or_404(Post.objects.select_related("user"), pk=post_id)

    try:
        ensure_can_message_post(post, request.user)
    except MessagingError as exc:
        messages.error(request, str(exc))
        if post.status == "published":
            return redirect(post.get_absolute_url())
        return redirect("core:index")

    existing = find_active_conversation(post, request.user)
    if existing and request.method == "GET":
        return redirect("messaging:thread", conversation_id=existing.pk)

    form = MessageForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        image_url = ""
        image_file = form.cleaned_data.get("image")
        if image_file:
            try:
                image_url = upload_image(image_file, prefix="messages")
            except ValueError as exc:
                form.add_error("image", str(exc))
        if not form.errors:
            try:
                conversation = get_or_create_conversation(post, request.user)
                send_message(
                    conversation,
                    request.user,
                    form.cleaned_data["body"],
                    image=image_url,
                )
                return redirect("messaging:thread", conversation_id=conversation.pk)
            except MessagingError as exc:
                messages.error(request, str(exc))
                return redirect(post.get_absolute_url())

    return render(
        request,
        "messaging/compose.html",
        {
            "post": post,
            "other_user": post.user,
            "form": form if form.errors else MessageForm(),
            "cities": CITIES,
            "category_labels": CATEGORY_LABELS,
        },
    )
