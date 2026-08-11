from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("beheeromgeving", "0030_product_source_last_updated"),
    ]

    operations = [
        migrations.AddField(
            model_name="productrevision",
            name="source_last_updated",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
