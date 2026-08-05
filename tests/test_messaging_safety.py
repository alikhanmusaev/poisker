from datetime import timedelta

import pytest

from accounts.models import UserBlock
from accounts.models import User
from django.utils import timezone
from messaging.models import Conversation, Message
from messaging.services import MessagingError, get_or_create_conversation, send_message


def _conversation(make_post, seller):
    buyer = User.objects.create_user(
        email="blocked-buyer@example.com",
        password="password12345",
        display_name="Buyer",
        phone="+79007778899",
    )
    post = make_post(status="published", expires_at=timezone.now() + timedelta(days=30))
    conversation = Conversation.objects.create(post=post, buyer=buyer, seller=seller)
    Message.objects.create(conversation=conversation, sender=buyer, body="Здравствуйте")
    return conversation, buyer, post


def test_blocking_user_prevents_new_messages(make_post, seller):
    conversation, buyer, _post = _conversation(make_post, seller)
    UserBlock.objects.create(blocker=buyer, blocked=seller)

    with pytest.raises(MessagingError):
        send_message(conversation, buyer, "Не должно отправиться")
    with pytest.raises(MessagingError):
        send_message(conversation, seller, "И это тоже")


def test_blocking_user_prevents_starting_new_chat(make_post, seller):
    _conversation, buyer, post = _conversation(make_post, seller)
    UserBlock.objects.create(blocker=seller, blocked=buyer)

    with pytest.raises(MessagingError):
        get_or_create_conversation(post, buyer)
