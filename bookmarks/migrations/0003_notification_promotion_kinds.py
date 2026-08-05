# Generated manually for promotion payment notifications.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("bookmarks", "0002_alter_notification_kind"),
    ]

    operations = [
        migrations.AlterField(
            model_name="notification",
            name="kind",
            field=models.CharField(
                choices=[
                    ("price_changed", "Изменение цены"),
                    ("post_unpublished", "Снятие объявления"),
                    ("category_new_post", "Новое в категории"),
                    ("moderation_approved", "Одобрено модерацией"),
                    ("moderation_rejected", "Отклонено модерацией"),
                    ("post_expired", "Срок истёк"),
                    ("new_review", "Новый отзыв"),
                    ("review_reply", "Ответ на отзыв"),
                    ("deal_confirm_request", "Подтвердите сделку"),
                    ("review_unlocked", "Можно оставить отзыв"),
                    ("review_reminder", "Напоминание об отзыве"),
                    ("promotion_paid", "Продвижение подключено"),
                    ("promotion_failed", "Оплата продвижения не прошла"),
                ],
                db_index=True,
                max_length=40,
            ),
        ),
    ]
