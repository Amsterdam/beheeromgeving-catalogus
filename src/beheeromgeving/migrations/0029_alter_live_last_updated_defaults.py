import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("beheeromgeving", "0028_datacontractrevisiondistribution"),
    ]

    operations = [
        migrations.AlterField(
            model_name="product",
            name="last_updated",
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name="datacontract",
            name="last_updated",
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]
