from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("listings", "0011_post_moderation_flags")]

    operations = [migrations.AddField(model_name="post", name="image_hashes", field=models.JSONField(blank=True, default=list))]
