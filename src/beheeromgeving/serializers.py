from rest_framework import serializers

from .models import APIDistribution, DataContract, DataTeam, Distribution, FileDistribution

# TODO: where is the source of this? maybe turn into model?
TAGS_CHOICES = (("bomen", "Bomen"), ("groen", "Groen"))


class DataTeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataTeam
        fields = "__all__"


class APIDistributionSerializer(serializers.ModelSerializer):
    class Meta:
        model = APIDistribution
        fields = ("api_type", "url")


class FileDistributionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileDistribution
        fields = ("file_format", "link")


class DistributionSerializer(serializers.ModelSerializer):
    files = FileDistributionSerializer(many=True, required=False)
    apis = APIDistributionSerializer(many=True, required=False)

    class Meta:
        model = Distribution
        fields = "__all__"


class DataContractSerializer(serializers.ModelSerializer):
    themes = serializers.MultipleChoiceField(
        choices=DataContract.THEME_CHOICES,
        label="Thema('s)",
        help_text="Thema's voor Data Producten zoals gedefinieerd als de thema's op nationaal "
        "niveau. Dit geeft de mogelijkheid om te koppelen op de nationale repository.",
    )
    tags = serializers.MultipleChoiceField(
        choices=TAGS_CHOICES,
        label="Zoekwoorden",
        help_text="Zoekwoorden of Tags die het Data Product of zijn inhoud beschrijven. Dit is "
        "bedoeld om de vindbaarheid in de Data Catalogus te ondersteunen. Het gaat om een "
        "logische groepering van Data Producten. De lijst met toegestane waarden wordt beheerd "
        "door het Data Platform",
    )
    owner = serializers.CharField(
        allow_null=True,
        label="Eigenaar",
        help_text="Standaard de PO van het datateam, maar kan hier overschreven worden. Maak "
        "leeg om te resetten naar de PO.",
    )
    distribution = DistributionSerializer()

    class Meta:
        model = DataContract
        fields = (
            "name",
            "description",
            "purpose",
            "themes",
            "tags",
            "datateam",
            "owner",
            "contact_email",
            "data_steward",
            "language",
            "confidentiality",
            "privacy",
            "crs",
            "refresh_period",
            "retainment_period",
            "start_date",
            "schema",
            "schema_url",
            "distribution",
            "version",
        )

    def validate(self, data):
        if self.partial:
            if data.get("crs", None):
                data["is_geo"] = data["crs"] != "NVT"
            if data.get("themes", None) is not None:
                data["themes"] = list(data["themes"])
            if data.get("tags", None) is not None:
                data["tags"] = list(data["tags"])
        else:
            data["is_geo"] = data["crs"] != "NVT"
            if not data.get("schema", None) and not data.get("schema_url", None):
                raise serializers.ValidationError("Either enter a schema, or a schema url.")
            data["themes"] = list(data["themes"])
            data["tags"] = list(data["tags"])

        if data.get("schema", None) and data.get("schema_url", None):
            raise serializers.ValidationError("Either enter a schema, or a schema url, not both.")
        return data

    def create(self, validated_data):
        distribution_data = validated_data.pop("distribution")
        files_data = distribution_data.pop("files", [])
        apis_data = distribution_data.pop("apis", [])
        distribution = Distribution.objects.create(**distribution_data)
        for file_data in files_data:
            FileDistribution.objects.create(distribution=distribution, **file_data)
        for api_data in apis_data:
            APIDistribution.objects.create(distribution=distribution, **api_data)
        return DataContract.objects.create(distribution=distribution, **validated_data)

    def update(self, instance, validated_data):
        distribution_data = validated_data.pop("distribution", None)
        if distribution_data:
            files_data = distribution_data.pop("files", [])
            apis_data = distribution_data.pop("apis", [])
            Distribution.objects.filter(id=instance.distribution.id).update(**distribution_data)

            # Replace the File/API distributions completely
            FileDistribution.objects.filter(distribution=instance.distribution).delete()
            for file_data in files_data:
                file_data.pop("distribution", None)
                FileDistribution.objects.create(distribution=instance.distribution, **file_data)
            APIDistribution.objects.filter(distribution=instance.distribution).delete()
            for api_data in apis_data:
                api_data.pop("distribution", None)
                APIDistribution.objects.create(distribution=instance.distribution, **api_data)

        owner = validated_data.pop("owner", None)
        DataContract.objects.filter(pk=instance.pk).update(
            distribution=instance.distribution, **validated_data
        )
        instance.refresh_from_db()
        instance.owner = owner
        instance.save()
        return instance
