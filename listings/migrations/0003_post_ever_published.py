from django.db import migrations, models


def mark_ever_published(apps, schema_editor):
    Post = apps.get_model("listings", "Post")
    Post.objects.filter(status__in=("published", "hidden", "expired")).update(ever_published=True)


class Migration(migrations.Migration):

    dependencies = [
        ("listings", "0002_post_slug_not_unique"),
    ]

    operations = [
        migrations.AddField(
            model_name="post",
            name="ever_published",
            field=models.BooleanField(db_index=True, default=False, verbose_name="Было опубликовано"),
        ),
        migrations.RunPython(mark_ever_published, migrations.RunPython.noop),
    ]
