from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("accounts", "0007_user_preferred_settlement")]
    operations = [migrations.CreateModel(name="UserBlock", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("created_at", models.DateTimeField(auto_now_add=True)), ("blocked", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="blocks_received", to=settings.AUTH_USER_MODEL)), ("blocker", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="blocks_created", to=settings.AUTH_USER_MODEL))]), migrations.AddConstraint(model_name="userblock", constraint=models.UniqueConstraint(fields=("blocker", "blocked"), name="accounts_unique_user_block"))]
