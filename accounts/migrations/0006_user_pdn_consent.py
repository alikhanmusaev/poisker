from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0005_user_email_verified"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="terms_accepted_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="Условия приняты"),
        ),
        migrations.AddField(
            model_name="user",
            name="pdn_consent_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="Согласие на ПДн"),
        ),
        migrations.AddField(
            model_name="user",
            name="pdn_consent_version",
            field=models.CharField(
                blank=True, default="", max_length=32, verbose_name="Версия согласия ПДн"
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="consent_ip",
            field=models.GenericIPAddressField(blank=True, null=True, verbose_name="IP согласия"),
        ),
    ]
