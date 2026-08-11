from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("beheeromgeving", "0029_alter_live_last_updated_defaults"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="source_last_updated",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
