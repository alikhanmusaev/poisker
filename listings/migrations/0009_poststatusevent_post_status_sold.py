from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("listings", "0008_promotion_stats"),
    ]

    operations = [
        migrations.CreateModel(
            name="PostStatusEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("previous_status", models.CharField(blank=True, max_length=20)),
                ("new_status", models.CharField(max_length=20)),
                ("reason", models.CharField(blank=True, max_length=80)),
                ("created_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="post_status_events", to=settings.AUTH_USER_MODEL)),
                ("post", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="status_events", to="listings.post")),
            ],
            options={"verbose_name": "Изменение статуса объявления", "verbose_name_plural": "Изменения статусов объявлений", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(model_name="poststatusevent", index=models.Index(fields=["post", "-created_at"], name="listings_po_post_id_2d1d71_idx")),
    ]
