from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("listings", "0010_rename_listings_po_post_id_2d1d71_idx_listings_po_post_id_c41f7b_idx_and_more")]

    operations = [
        migrations.AddField(
            model_name="post",
            name="moderation_flags",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
