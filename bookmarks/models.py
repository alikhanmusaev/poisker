from django.conf import settings
from django.db import models
from django.utils import timezone


class PostBookmark(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="post_bookmarks",
    )
    post = models.ForeignKey(
        "listings.Post",
        on_delete=models.CASCADE,
        related_name="bookmarks",
    )
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "post"], name="bookmarks_unique_user_post"),
        ]
        ordering = ["-created_at"]
        verbose_name = "Закладка объявления"
        verbose_name_plural = "Закладки объявлений"

    def __str__(self):
        return f"{self.user_id} → {self.post_id}"


class CategoryBookmark(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="category_bookmarks",
    )
    category = models.CharField(max_length=50, db_index=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "category"], name="bookmarks_unique_user_category"),
        ]
        ordering = ["-created_at"]
        verbose_name = "Закладка категории"
        verbose_name_plural = "Закладки категорий"

    def __str__(self):
        return f"{self.user_id} → {self.category}"


class Notification(models.Model):
    KIND_PRICE_CHANGED = "price_changed"
    KIND_POST_UNPUBLISHED = "post_unpublished"
    KIND_CATEGORY_NEW_POST = "category_new_post"
    KIND_MODERATION_APPROVED = "moderation_approved"
    KIND_MODERATION_REJECTED = "moderation_rejected"
    KIND_POST_EXPIRED = "post_expired"
    KIND_NEW_REVIEW = "new_review"
    KIND_REVIEW_REPLY = "review_reply"
    KIND_CHOICES = [
        (KIND_PRICE_CHANGED, "Изменение цены"),
        (KIND_POST_UNPUBLISHED, "Снятие объявления"),
        (KIND_CATEGORY_NEW_POST, "Новое в категории"),
        (KIND_MODERATION_APPROVED, "Одобрено модерацией"),
        (KIND_MODERATION_REJECTED, "Отклонено модерацией"),
        (KIND_POST_EXPIRED, "Срок истёк"),
        (KIND_NEW_REVIEW, "Новый отзыв"),
        (KIND_REVIEW_REPLY, "Ответ на отзыв"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    kind = models.CharField(max_length=40, choices=KIND_CHOICES, db_index=True)
    title = models.CharField(max_length=200)
    body = models.CharField(max_length=500, blank=True)
    post = models.ForeignKey(
        "listings.Post",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )
    category = models.CharField(max_length=50, blank=True, db_index=True)
    payload = models.JSONField(default=dict, blank=True)
    read_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "read_at", "-created_at"]),
        ]
        verbose_name = "Уведомление"
        verbose_name_plural = "Уведомления"

    def __str__(self):
        return f"{self.kind}: {self.title}"

    @property
    def is_unread(self) -> bool:
        return self.read_at is None
