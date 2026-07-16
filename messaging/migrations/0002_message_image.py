from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("messaging", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="message",
            name="image",
            field=models.CharField(blank=True, max_length=512, verbose_name="Фото"),
        ),
        migrations.AlterField(
            model_name="message",
            name="body",
            field=models.TextField(blank=True, max_length=2000, verbose_name="Текст"),
        ),
    ]
