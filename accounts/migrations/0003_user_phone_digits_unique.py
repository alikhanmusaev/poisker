from django.db import migrations, models

from core.phone import normalize_phone, phone_digits


def populate_unique_phone_digits(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    used = set()
    for user in User.objects.order_by("id"):
        digits = phone_digits(user.phone)
        if digits in used:
            user.phone = normalize_phone(f"79{user.pk:09d}"[-10:])
            digits = phone_digits(user.phone)
            while digits in used:
                user.phone = normalize_phone(f"78{user.pk:09d}"[-10:])
                digits = phone_digits(user.phone)
        used.add(digits)
        user.phone_digits = digits
        user.save(update_fields=["phone", "phone_digits"])


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_user_phone_required"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="phone_digits",
            field=models.CharField(
                editable=False,
                max_length=11,
                null=True,
                verbose_name="Телефон (цифры)",
            ),
        ),
        migrations.RunPython(populate_unique_phone_digits, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="user",
            name="phone_digits",
            field=models.CharField(editable=False, max_length=11, unique=True, verbose_name="Телефон (цифры)"),
        ),
    ]
