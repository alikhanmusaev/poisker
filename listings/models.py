import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from listings.constants import CONDITION_CHOICES


class Post(models.Model):
    STATUS_CHOICES = [
        ("draft", "Черновик"),
        ("pending", "На модерации"),
        ("published", "Опубликовано"),
        ("hidden", "Снято с публикации"),
        ("expired", "Истекло"),
        ("deleted", "Удалено"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="posts",
        verbose_name="Автор",
    )
    title = models.CharField(max_length=200)
    body = models.TextField()
    category = models.CharField(max_length=50, db_index=True)
    city = models.CharField(max_length=50, db_index=True)
    condition = models.CharField(
        "Состояние",
        max_length=10,
        choices=CONDITION_CHOICES,
        default="used",
        db_index=True,
    )
    price = models.PositiveIntegerField(null=True, blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    slug = models.SlugField(max_length=120, null=True, blank=True, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending", db_index=True)
    ever_published = models.BooleanField("Было опубликовано", default=False, db_index=True)
    published_at = models.DateTimeField("Опубликовано", null=True, blank=True, db_index=True)
    moderation_note = models.CharField("Комментарий модератора", max_length=400, blank=True)
    images = models.JSONField(default=list, blank=True)
    cover_index = models.PositiveSmallIntegerField(default=0)
    pending_revision = models.JSONField(null=True, blank=True)
    views = models.PositiveIntegerField(default=0)
    contact_clicks = models.PositiveIntegerField(default=0)
    reports_count = models.PositiveIntegerField(default=0)
    rank_score = models.FloatField(default=0.0, db_index=True)
    has_photo = models.BooleanField(default=False)
    paid_until = models.DateTimeField(null=True, blank=True)
    paid_boost = models.FloatField(default=1.0)
    bumped_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["city", "category", "rank_score"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["status", "expires_at"]),
        ]
        verbose_name = "Объявление"
        verbose_name_plural = "Объявления"

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        from listings.services.seo_urls import post_public_url

        return post_public_url(self)

    def save(self, *args, **kwargs):
        if self.status == "published":
            self.ever_published = True
        super().save(*args, **kwargs)

    @property
    def seller_name(self):
        return self.user.display_name

    @property
    def is_promoted(self):
        return bool(self.paid_until and self.paid_until > timezone.now())

    @property
    def phone_masked(self):
        phone = self.contact_phone or self.user.phone
        if not phone:
            return "—"
        digits = "".join(c for c in phone if c.isdigit())
        if len(digits) < 4:
            return phone
        return f"+7 *** ***-{digits[-4:-2]}-{digits[-2:]}"

    def to_search_doc(self) -> dict:
        return {
            "id": str(self.pk),
            "title": self.title,
            "body": self.body,
            "category": self.category,
            "city": self.city,
            "price": self.price,
            "status": self.status,
            "has_photo": self.has_photo,
            "rank_score": self.rank_score,
            "created_at": int(self.created_at.timestamp()) if self.created_at else 0,
            "expires_at": int(self.expires_at.timestamp()) if self.expires_at else 0,
            "paid_boost": self.paid_boost,
        }


class Report(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="reports")
    reason = models.CharField(max_length=50)
    comment = models.TextField(blank=True)
    reporter_ip = models.GenericIPAddressField(null=True, blank=True)
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reports",
    )
    status = models.CharField(max_length=20, default="new", db_index=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Жалоба"
        verbose_name_plural = "Жалобы"


class Promotion(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="promotions")
    type = models.CharField(max_length=20)
    amount = models.PositiveIntegerField()
    status = models.CharField(max_length=20, default="pending", db_index=True)
    payment_ref = models.CharField(max_length=100, blank=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Продвижение"
        verbose_name_plural = "Продвижения"
