import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class SellerReview(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews_written",
        verbose_name="Автор отзыва",
    )
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews_received",
        verbose_name="Продавец",
    )
    conversation = models.ForeignKey(
        "messaging.Conversation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviews",
        verbose_name="Переписка",
    )
    post = models.ForeignKey(
        "listings.Post",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviews",
        verbose_name="Объявление",
    )
    rating = models.PositiveSmallIntegerField(
        "Оценка",
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    comment = models.TextField("Комментарий", max_length=1000, blank=True)
    reply_text = models.TextField("Ответ продавца", max_length=1000, blank=True)
    replied_at = models.DateTimeField("Ответ дан", null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["reviewer", "seller"],
                name="reviews_unique_reviewer_seller",
            ),
            models.CheckConstraint(
                condition=models.Q(rating__gte=1, rating__lte=5),
                name="reviews_rating_range",
            ),
        ]
        verbose_name = "Отзыв о продавце"
        verbose_name_plural = "Отзывы о продавцах"

    def __str__(self):
        return f"{self.reviewer_id} → {self.seller_id}: {self.rating}"


class PhoneReveal(models.Model):
    """Buyer opened seller phone on a listing — unlocks review after a delay."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="phone_reveals",
        verbose_name="Покупатель",
    )
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="phone_reveals_as_seller",
        verbose_name="Продавец",
    )
    post = models.ForeignKey(
        "listings.Post",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="phone_reveals",
        verbose_name="Объявление",
    )
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["reviewer", "seller"],
                name="reviews_unique_phone_reveal_reviewer_seller",
            ),
        ]
        verbose_name = "Просмотр телефона"
        verbose_name_plural = "Просмотры телефона"

    def __str__(self):
        return f"{self.reviewer_id} → {self.seller_id} @ {self.created_at}"
