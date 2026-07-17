import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(
        "listings.Post",
        on_delete=models.CASCADE,
        related_name="conversations",
        verbose_name="Объявление",
    )
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="buyer_conversations",
        verbose_name="Покупатель",
    )
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="seller_conversations",
        verbose_name="Продавец",
    )
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(default=timezone.now, db_index=True)
    buyer_hidden_at = models.DateTimeField(null=True, blank=True)
    seller_hidden_at = models.DateTimeField(null=True, blank=True)
    buyer_deal_confirmed_at = models.DateTimeField(null=True, blank=True)
    seller_deal_confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(fields=["post", "buyer"], name="messaging_unique_post_buyer"),
        ]
        verbose_name = "Переписка"
        verbose_name_plural = "Переписки"

    def __str__(self):
        return f"{self.post.title} — {self.buyer_id} / {self.seller_id}"

    def other_participant(self, user):
        if user.id == self.buyer_id:
            return self.seller
        return self.buyer

    def involves(self, user) -> bool:
        return user.id in (self.buyer_id, self.seller_id)

    def is_hidden_for(self, user) -> bool:
        if user.id == self.buyer_id:
            return self.buyer_hidden_at is not None
        if user.id == self.seller_id:
            return self.seller_hidden_at is not None
        return True

    def hide_for(self, user) -> None:
        now = timezone.now()
        if user.id == self.buyer_id:
            self.buyer_hidden_at = now
            Conversation.objects.filter(pk=self.pk).update(buyer_hidden_at=now)
        elif user.id == self.seller_id:
            self.seller_hidden_at = now
            Conversation.objects.filter(pk=self.pk).update(seller_hidden_at=now)

    def unhide_for(self, user) -> None:
        if user.id == self.buyer_id and self.buyer_hidden_at is not None:
            self.buyer_hidden_at = None
            Conversation.objects.filter(pk=self.pk).update(buyer_hidden_at=None)
        elif user.id == self.seller_id and self.seller_hidden_at is not None:
            self.seller_hidden_at = None
            Conversation.objects.filter(pk=self.pk).update(seller_hidden_at=None)

    def unhide_all(self) -> None:
        if self.buyer_hidden_at is None and self.seller_hidden_at is None:
            return
        self.buyer_hidden_at = None
        self.seller_hidden_at = None
        Conversation.objects.filter(pk=self.pk).update(
            buyer_hidden_at=None,
            seller_hidden_at=None,
        )

    @property
    def both_deal_confirmed(self) -> bool:
        return (
            self.buyer_deal_confirmed_at is not None
            and self.seller_deal_confirmed_at is not None
        )

    def deal_confirmed_by(self, user) -> bool:
        if user.id == self.buyer_id:
            return self.buyer_deal_confirmed_at is not None
        if user.id == self.seller_id:
            return self.seller_deal_confirmed_at is not None
        return False


class Message(models.Model):
    id = models.BigAutoField(primary_key=True)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name="Переписка",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_messages",
        verbose_name="Отправитель",
    )
    body = models.TextField("Текст", max_length=2000, blank=True)
    image = models.CharField("Фото", max_length=512, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["conversation", "created_at"]),
            models.Index(fields=["conversation", "read_at"]),
        ]
        verbose_name = "Сообщение"
        verbose_name_plural = "Сообщения"

    def __str__(self):
        if self.body:
            return self.body[:60]
        if self.image:
            return "[фото]"
        return ""

    @property
    def preview_text(self):
        if self.body:
            return self.body
        if self.image:
            return "Фото"
        return ""
