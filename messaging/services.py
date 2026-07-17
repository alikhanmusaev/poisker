from django.db.models import Count, Exists, OuterRef, Q, Subquery
from django.utils import timezone

from listings.models import Post
from messaging.models import Conversation, Message


class MessagingError(Exception):
    pass


def unread_messages_count(user) -> int:
    if not user.is_authenticated:
        return 0
    visible = Conversation.objects.filter(Q(buyer=user) | Q(seller=user)).filter(
        Q(buyer=user, buyer_hidden_at__isnull=True)
        | Q(seller=user, seller_hidden_at__isnull=True)
    )
    return Message.objects.filter(
        conversation__in=visible,
        read_at__isnull=True,
    ).exclude(sender=user).count()


def get_or_create_conversation(post: Post, buyer) -> Conversation:
    ensure_can_message_post(post, buyer)

    conversation, _created = Conversation.objects.get_or_create(
        post=post,
        buyer=buyer,
        defaults={"seller_id": post.user_id},
    )
    return conversation


def ensure_can_message_post(post: Post, buyer) -> None:
    if buyer.is_blocked:
        raise MessagingError("Аккаунт заблокирован.")
    if post.user_id == buyer.id:
        raise MessagingError("Нельзя написать самому себе по своему объявлению.")
    if post.status != "published":
        raise MessagingError("По этому объявлению пока нельзя написать.")


def find_active_conversation(post: Post, buyer):
    return (
        Conversation.objects.filter(post=post, buyer=buyer, buyer_hidden_at__isnull=True)
        .filter(has_visible_messages_q())
        .first()
    )


def get_conversation_for_user(user, conversation_id) -> Conversation:
    conversation = (
        Conversation.objects.select_related("post", "buyer", "seller")
        .filter(pk=conversation_id)
        .filter(Q(buyer=user) | Q(seller=user))
        .first()
    )
    if not conversation:
        raise MessagingError("Переписка не найдена.")
    if conversation.is_hidden_for(user):
        raise MessagingError("Переписка не найдена.")
    return conversation


def send_message(conversation: Conversation, sender, body: str = "", *, image: str = "") -> Message:
    if sender.is_blocked:
        raise MessagingError("Аккаунт заблокирован.")
    if not conversation.involves(sender):
        raise MessagingError("Нет доступа к переписке.")

    body = (body or "").strip()
    image = (image or "").strip()
    if not body and not image:
        raise MessagingError("Введите текст или прикрепите фото.")

    now = timezone.now()
    message = Message.objects.create(
        conversation=conversation,
        sender=sender,
        body=body,
        image=image,
        created_at=now,
    )
    conversation.unhide_all()
    Conversation.objects.filter(pk=conversation.pk).update(updated_at=now)
    conversation.updated_at = now

    recipient = conversation.seller if sender.id == conversation.buyer_id else conversation.buyer
    if recipient and recipient.id != sender.id:
        try:
            from notifications.services import push_for_new_message

            push_for_new_message(
                recipient=recipient,
                conversation=conversation,
                sender=sender,
                message=message,
            )
        except Exception:
            pass
    return message


def mark_conversation_read(conversation: Conversation, reader) -> None:
    if not conversation.involves(reader):
        return
    now = timezone.now()
    Message.objects.filter(
        conversation=conversation,
        read_at__isnull=True,
    ).exclude(sender=reader).update(read_at=now)


def hide_conversation(conversation: Conversation, user) -> None:
    if not conversation.involves(user):
        raise MessagingError("Нет доступа к переписке.")
    conversation.hide_for(user)


def confirm_deal_completed(conversation: Conversation, user) -> Conversation:
    if getattr(user, "is_blocked", False):
        raise MessagingError("Аккаунт заблокирован.")
    if not conversation.involves(user):
        raise MessagingError("Нет доступа к переписке.")
    if not Conversation.objects.filter(pk=conversation.pk).filter(has_visible_messages_q()).exists():
        raise MessagingError("Сначала обменяйтесь сообщениями в чате.")

    now = timezone.now()
    already_confirmed = conversation.deal_confirmed_by(user)
    if user.id == conversation.buyer_id:
        if conversation.buyer_deal_confirmed_at is not None:
            return conversation
        Conversation.objects.filter(pk=conversation.pk).update(buyer_deal_confirmed_at=now)
        conversation.buyer_deal_confirmed_at = now
    elif user.id == conversation.seller_id:
        if conversation.seller_deal_confirmed_at is not None:
            return conversation
        Conversation.objects.filter(pk=conversation.pk).update(seller_deal_confirmed_at=now)
        conversation.seller_deal_confirmed_at = now

    if not already_confirmed:
        from reviews.services import handle_deal_confirmation_side_effects

        handle_deal_confirmation_side_effects(conversation, user)
    return conversation


def has_visible_messages_q():
    return Exists(
        Message.objects.filter(conversation=OuterRef("pk")).exclude(body="", image="")
    )


def delete_empty_conversations(user) -> int:
    """Remove chats that were opened but never got a real message."""
    empty = (
        Conversation.objects.filter(Q(buyer=user) | Q(seller=user))
        .exclude(has_visible_messages_q())
    )
    count, _ = empty.delete()
    return count


def visible_conversations_q(user):
    return Q(buyer=user, buyer_hidden_at__isnull=True) | Q(
        seller=user, seller_hidden_at__isnull=True
    )


def inbox_conversations(user):
    delete_empty_conversations(user)
    last_message = (
        Message.objects.filter(conversation=OuterRef("pk"))
        .exclude(body="", image="")
        .order_by("-created_at")
    )
    return (
        Conversation.objects.filter(visible_conversations_q(user))
        .filter(has_visible_messages_q())
        .select_related("post", "buyer", "seller")
        .annotate(
            last_message_body=Subquery(last_message.values("body")[:1]),
            last_message_image=Subquery(last_message.values("image")[:1]),
            last_message_at=Subquery(last_message.values("created_at")[:1]),
            last_message_read_at=Subquery(last_message.values("read_at")[:1]),
            last_message_sender_id=Subquery(last_message.values("sender_id")[:1]),
            unread_count=Count(
                "messages",
                filter=Q(messages__read_at__isnull=True) & ~Q(messages__sender_id=user.id),
            ),
        )
        .order_by("-updated_at")
    )
