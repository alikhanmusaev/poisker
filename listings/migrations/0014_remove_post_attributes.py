from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("listings", "0013_post_attributes")]
    operations = [migrations.RemoveField(model_name="post", name="attributes")]
