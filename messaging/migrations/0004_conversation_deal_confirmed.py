from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("messaging", "0003_conversation_hidden"),
    ]

    operations = [
        migrations.AddField(
            model_name="conversation",
            name="buyer_deal_confirmed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="conversation",
            name="seller_deal_confirmed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
