# Generated manually for seller rating aggregates

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_user_phone_digits_unique"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="rating_avg",
            field=models.FloatField(default=0.0, verbose_name="Средняя оценка"),
        ),
        migrations.AddField(
            model_name="user",
            name="rating_count",
            field=models.PositiveIntegerField(default=0, verbose_name="Число отзывов"),
        ),
    ]
