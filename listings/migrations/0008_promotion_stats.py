# Generated manually for Promotion stats fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("listings", "0007_post_settlement"),
    ]

    operations = [
        migrations.AddField(
            model_name="promotion",
            name="impressions",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="promotion",
            name="clicks",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="promotion",
            name="last_shown_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
