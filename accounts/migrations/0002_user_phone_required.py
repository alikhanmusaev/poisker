from django.db import migrations, models

from core.phone import normalize_phone


def fill_missing_phones(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    Post = apps.get_model("listings", "Post")
    for user in User.objects.filter(phone=""):
        user.phone = "+7 (900) 000-00-00"
        user.save(update_fields=["phone"])
    for post in Post.objects.all():
        user = User.objects.get(pk=post.user_id)
        post.contact_phone = normalize_phone(user.phone)
        post.save(update_fields=["contact_phone"])


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
        ("listings", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(fill_missing_phones, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="user",
            name="phone",
            field=models.CharField(max_length=20, verbose_name="Телефон"),
        ),
    ]
