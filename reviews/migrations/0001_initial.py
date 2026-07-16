# Generated manually for SellerReview

import django.core.validators
import django.db.models.deletion
import django.utils.timezone
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("accounts", "0004_user_rating"),
        ("listings", "0005_post_published_at_moderation_note"),
        ("messaging", "0003_conversation_hidden"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SellerReview",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "rating",
                    models.PositiveSmallIntegerField(
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(5),
                        ],
                        verbose_name="Оценка",
                    ),
                ),
                (
                    "comment",
                    models.TextField(blank=True, max_length=1000, verbose_name="Комментарий"),
                ),
                (
                    "created_at",
                    models.DateTimeField(db_index=True, default=django.utils.timezone.now),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "conversation",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reviews",
                        to="messaging.conversation",
                        verbose_name="Переписка",
                    ),
                ),
                (
                    "post",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reviews",
                        to="listings.post",
                        verbose_name="Объявление",
                    ),
                ),
                (
                    "reviewer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reviews_written",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Автор отзыва",
                    ),
                ),
                (
                    "seller",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reviews_received",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Продавец",
                    ),
                ),
            ],
            options={
                "verbose_name": "Отзыв о продавце",
                "verbose_name_plural": "Отзывы о продавцах",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="sellerreview",
            constraint=models.UniqueConstraint(
                fields=("reviewer", "seller"),
                name="reviews_unique_reviewer_seller",
            ),
        ),
        migrations.AddConstraint(
            model_name="sellerreview",
            constraint=models.CheckConstraint(
                condition=models.Q(rating__gte=1, rating__lte=5),
                name="reviews_rating_range",
            ),
        ),
    ]
