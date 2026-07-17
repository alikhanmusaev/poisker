from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("listings", "0005_post_published_at_moderation_note"),
    ]

    operations = [
        migrations.AddField(
            model_name="post",
            name="condition",
            field=models.CharField(
                choices=[("used", "Б/У"), ("new", "Новый")],
                db_index=True,
                default="used",
                max_length=10,
                verbose_name="Состояние",
            ),
        ),
    ]
