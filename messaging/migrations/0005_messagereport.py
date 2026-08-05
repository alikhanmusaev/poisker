from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [("messaging", "0004_conversation_deal_confirmed"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [migrations.CreateModel(name="MessageReport", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("reason", models.CharField(default="other", max_length=40)), ("status", models.CharField(db_index=True, default="new", max_length=20)), ("created_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)), ("message", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reports", to="messaging.message")), ("reporter", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="message_reports", to=settings.AUTH_USER_MODEL))]), migrations.AddConstraint(model_name="messagereport", constraint=models.UniqueConstraint(fields=("message", "reporter"), name="messaging_unique_message_report"))]
