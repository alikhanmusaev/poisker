from django.db import migrations, models
from django.db.models import F


def backfill_published_at(apps, schema_editor):
    Post = apps.get_model("listings", "Post")
    Post.objects.filter(status="published", published_at__isnull=True).update(
        published_at=F("updated_at")
    )
    Post.objects.filter(status="published", published_at__isnull=True).update(
        published_at=F("created_at")
    )


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("listings", "0004_alter_post_status_label"),
    ]

    operations = [
        migrations.AddField(
            model_name="post",
            name="published_at",
            field=models.DateTimeField(
                blank=True, db_index=True, null=True, verbose_name="Опубликовано"
            ),
        ),
        migrations.AddField(
            model_name="post",
            name="moderation_note",
            field=models.CharField(
                blank=True, max_length=400, verbose_name="Комментарий модератора"
            ),
        ),
        migrations.RunPython(backfill_published_at, migrations.RunPython.noop),
    ]
