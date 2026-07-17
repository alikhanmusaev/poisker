from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_user_rating"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="email_verified",
            field=models.BooleanField(
                db_index=True,
                default=True,
                verbose_name="Email подтверждён",
            ),
        ),
    ]
