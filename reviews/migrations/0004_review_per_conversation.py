from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("reviews", "0003_sellerreview_reply"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="sellerreview",
            name="reviews_unique_reviewer_seller",
        ),
        migrations.AddConstraint(
            model_name="sellerreview",
            constraint=models.UniqueConstraint(
                fields=("reviewer", "conversation"),
                name="reviews_unique_reviewer_conversation",
            ),
        ),
    ]
