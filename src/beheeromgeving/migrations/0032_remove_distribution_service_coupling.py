from django.db import migrations


def delete_service_linked_distributions(apps, schema_editor):
    Distribution = apps.get_model("beheeromgeving", "Distribution")
    DataContractRevisionDistribution = apps.get_model(
        "beheeromgeving", "DataContractRevisionDistribution"
    )

    Distribution.objects.filter(access_service_id__isnull=False).delete()
    DataContractRevisionDistribution.objects.filter(access_service_id__isnull=False).delete()


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("beheeromgeving", "0031_productrevision_source_last_updated"),
    ]

    operations = [
        # PostgreSQL keeps FK trigger work from the deletes pending until commit.
        # This migration must commit the data cleanup before altering Distribution.
        migrations.RunPython(
            delete_service_linked_distributions,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.RemoveField(
            model_name="distribution",
            name="access_service",
        ),
        migrations.RemoveField(
            model_name="datacontractrevisiondistribution",
            name="access_service_id",
        ),
    ]
