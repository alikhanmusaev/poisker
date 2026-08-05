from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("listings", "0012_post_image_hashes")]
    operations = [migrations.AddField(model_name="post", name="attributes", field=models.JSONField(blank=True, default=dict))]
