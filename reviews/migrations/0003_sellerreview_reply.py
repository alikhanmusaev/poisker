# Generated manually for seller reply on reviews

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("reviews", "0002_phonereveal"),
    ]

    operations = [
        migrations.AddField(
            model_name="sellerreview",
            name="reply_text",
            field=models.TextField(blank=True, max_length=1000, verbose_name="Ответ продавца"),
        ),
        migrations.AddField(
            model_name="sellerreview",
            name="replied_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="Ответ дан"),
        ),
    ]
