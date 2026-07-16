# Generated manually for PhoneReveal

import django.db.models.deletion
import django.utils.timezone
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("listings", "0005_post_published_at_moderation_note"),
        ("reviews", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="PhoneReveal",
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
                    "created_at",
                    models.DateTimeField(db_index=True, default=django.utils.timezone.now),
                ),
                (
                    "post",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="phone_reveals",
                        to="listings.post",
                        verbose_name="Объявление",
                    ),
                ),
                (
                    "reviewer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="phone_reveals",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Покупатель",
                    ),
                ),
                (
                    "seller",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="phone_reveals_as_seller",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Продавец",
                    ),
                ),
            ],
            options={
                "verbose_name": "Просмотр телефона",
                "verbose_name_plural": "Просмотры телефона",
            },
        ),
        migrations.AddConstraint(
            model_name="phonereveal",
            constraint=models.UniqueConstraint(
                fields=("reviewer", "seller"),
                name="reviews_unique_phone_reveal_reviewer_seller",
            ),
        ),
    ]
