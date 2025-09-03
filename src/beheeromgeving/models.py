from __future__ import annotations

from django.contrib.postgres.fields import ArrayField
from django.core.validators import EmailValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from domain import enums, objects


class Product(models.Model):
    name = models.CharField(
        _("Naam"),
        unique=True,
        blank=True,
        null=True,
        max_length=64,
        help_text="De naam van het Product. Deze moet uniek zijn",
    )
    description = models.TextField(
        _("Beschrijving"),
        blank=True,
        null=True,
        help_text="Beschrijving en betekenis van het Data Product",
    )
    type = models.CharField(
        _("Product type"), max_length=1, choices=enums.ProductType.choices(), null=True, blank=True
    )
    themes = ArrayField(
        models.CharField(_("Thema('s)"), max_length=32, choices=enums.Theme.choices()),
        null=True,
        blank=True,
        help_text="Thema's voor Data Producten zoals gedefinieerd als de thema's op nationaal "
        "niveau. Dit geeft de mogelijkheid om te koppelen op de nationale repository.",
    )
    tags = ArrayField(
        models.CharField(_("Zoekwoorden"), max_length=32),
        null=True,
        blank=True,
        help_text="Zoekwoorden of Tags die het Data Product of zijn inhoud beschrijven. Dit is "
        "bedoeld om de vindbaarheid in de Data Catalogus te ondersteunen. Het gaat om een "
        "logische groepering van Data Producten.",
    )
    team: Team = models.ForeignKey(
        "Team",
        on_delete=models.CASCADE,
        related_name="products",
        help_text="Het team verantwoordelijk voor en gekoppeld aan het Data Product",
    )
    _owner = models.CharField(
        _("Eigenaar"),
        max_length=64,
        null=True,
        blank=True,
        help_text="De eigenaar van het Data Product. Standaard is dit de Product Owner van het "
        "betreffende Datateam, tenzij anders overeengekomen. Pas in dat geval de waarde aan",
    )
    publication_status = models.CharField(
        _("Publicatiestatus"),
        max_length=1,
        choices=enums.PublicationStatus.choices(),
        null=True,
        blank=True,
    )
    refresh_period = models.CharField(
        _("Ververstermijn"),
        max_length=64,
        null=True,
        blank=True,
        help_text="Om de hoeveel tijd de data in het Data Product ververst wordt",
    )
    has_personal_data = models.BooleanField(_("Bevat Persoonsgegevens"), default=False, null=True)
    has_special_personal_data = models.BooleanField(
        _("Bevat Bijzondere Persoonsgegevens"), default=False, null=True
    )
    last_updated = models.DateTimeField(auto_now=True)

    # Only for Dataproducts (type = "D")
    language = models.CharField(
        _("Taal"),
        choices=enums.Language.choices(),
        null=True,
        blank=True,
        help_text="De gebruikte taal in de inhoud van het Data Product",
    )
    schema_url = models.URLField(
        _("Amsterdam Schema Dataproduct verwijzing (url)"),
        blank=True,
        null=True,
        help_text="Verwijzing naar een dataset beschreven in Amsterdam Schema. Dit is alleen een "
        "vervanging voor het schema, niet de rest van het Data Contract. Als het 'Schema' veld is "
        "ingevuld en je geen gebruik maakt van Amsterdam Schema, dan blijft dit veld leeg",
    )
    is_geo = models.BooleanField(
        _("Geo Data"),
        help_text="Of het Data Product al dan niet geografische data bevat",
        blank=True,
        null=True,
    )
    sources = models.ManyToManyField("self", symmetrical=False, related_name="sinks")

    def __str__(self):
        return self.name or str(self.id)

    @property
    def owner(self):
        return self._owner or self.team.po_name

    @owner.setter
    def owner(self, value):
        if value and value != self.team.po_name:
            self._owner = value
        else:
            self._owner = None

    def to_domain(self):
        return objects.Product(
            id=self.id,
            type=self.type,
            name=self.name,
            description=self.description,
            team_id=self.team.id if self.team else None,
            language=self.language,
            is_geo=self.is_geo,
            schema_url=self.schema_url,
            contracts=[c.to_domain() for c in self.contracts.all()],
            themes=self.themes,
            tags=self.tags,
            last_updated=self.last_updated,
            has_personal_data=self.has_personal_data,
            has_special_personal_data=self.has_special_personal_data,
            refresh_period=self.refresh_period,
            publication_status=self.publication_status,
            owner=self.owner,
            services=[s.to_domain() for s in self.services.all()],
            sources=[s.id for s in self.sources.all()],
            sinks=[s.id for s in self.sinks.all()],
        )

    @classmethod
    def from_domain(cls, product: objects.Product):
        instance, _created = cls.objects.filter(pk=product.id).update_or_create(
            pk=product.id, defaults=product.items()
        )
        instance.owner = product.owner
        instance.save()
        return instance.to_domain()


class DataContract(models.Model):
    product: Product = models.ForeignKey(
        "Product",
        on_delete=models.CASCADE,
        help_text="Het Product waar dit contract bij hoort",
        related_name="contracts",
    )
    name = models.CharField(
        _("Naam"),
        unique=True,
        blank=True,
        null=True,
        max_length=64,
        help_text="De naam van het Data Contract. Deze moet uniek zijn",
    )
    description = models.TextField(
        _("Beschrijving"),
        blank=True,
        null=True,
        help_text="Beschrijving en betekenis van het Data Contract",
    )
    publication_status = models.CharField(
        _("Publicatiestatus"),
        max_length=1,
        blank=True,
        null=True,
        choices=enums.PublicationStatus.choices(),
    )
    purpose = models.TextField(
        _("Doelbinding"),
        blank=True,
        null=True,
        help_text="Beschrijf hier de doelbinding aan de hand van de use-case(s) waarvoor dit Data"
        " Contract is bedoeld en zijn bestaansrecht aan ontleent. Het uitgangspunt van doelbinding"
        " is, dat gegevens worden verwerkt en verzameld voor een welbepaald, uitdrukkelijk "
        "omschreven en gerechtvaardigde doel. 'Welbepaald en uitdrukkelijk omschreven' houdt in "
        "dat men geen gegevens mag verzamelen zonder een precieze doelomschrijving",
    )
    conditions = models.TextField(
        _("Voorwaarden"),
        blank=True,
        null=True,
        help_text="De voorwaarden van het datacontract",
    )
    data_steward = models.CharField(
        _("Business Data Steward"),
        blank=True,
        null=True,
        help_text="Contact E-mail adres van de verantwoordelijke Data Steward in de business",
        validators=[EmailValidator],
    )
    has_personal_data = models.BooleanField(_("Bevat Persoonsgegevens"), default=False, null=True)
    has_special_personal_data = models.BooleanField(
        _("Bevat Bijzondere Persoonsgegevens"), default=False, null=True
    )
    last_updated = models.DateTimeField(auto_now=True)
    confidentiality = models.CharField(
        _("Vertrouwelijkheidsniveau"),
        choices=enums.ConfidentialityLevel.choices(),
        blank=True,
        null=True,
        help_text="Het niveau van vertrouwelijkheid van de data in het Data Contract. Vereiste "
        "voor BBN",
    )

    retainment_period = models.IntegerField(
        _("Bewaartermijn in maanden"),
        blank=True,
        null=True,
        help_text="Om te voldoen aan de duurzame toegankelijkheidseisen (DUTO) van de overheid is "
        "het nodig om een bewaartermijn vast te leggen voor Data Producten zodat het Datateam hun "
        "omgeving hierop kan inrichten en de data te verwijderen wanneer dat nodig is",
    )
    start_date = models.DateField(
        _("Startdatum Contract"),
        blank=True,
        null=True,
        help_text="Datum waarop het Datacontract ingaat, en dus actief wordt. Deze datum kan in de"
        " toekomst liggen en kan een andere datum zijn dan de aanmaak datum van het Data Product. "
        "Dit is van belang wanneer er een nieuwe versie van het datacontract wordt gemaakt. Dit is"
        " geen systeemveld (zoals Aanmaak -en Wijzigingsdatum) en moet daarom separaat worden "
        "opgegeven. Wanneer het de innitiele versie van het Data Product betreft, vul hier dan de "
        "aanmaakdatum van het contract in. Wanneer het Data Product gemigreerd is vanaf de oude "
        "Data Catalogus, vul hier dan de publicatiedatum van de oude catalogus (Issued) in.",
    )
    profile = models.URLField(
        _("Amsterdam Schema Profiel verwijzing (url)"),
        blank=True,
        null=True,
        help_text="Verwijzing naar een profiel beschreven in Amsterdam Schema.",
    )

    def __str__(self):
        return self.name or str(self.id)

    @property
    def contact_email(self):
        return self.product.team.contact_email

    def to_domain(self):
        return objects.DataContract(
            id=self.id,
            publication_status=self.publication_status,
            purpose=self.purpose,
            name=self.name,
            description=self.description,
            contact_email=self.contact_email,
            business_data_steward=self.data_steward,
            last_updated=self.last_updated,
            has_personal_data=self.has_personal_data,
            has_special_personal_data=self.has_special_personal_data,
            profile=self.profile,
            confidentiality_level=self.confidentiality,
            start_date=self.start_date,
            retainment_period=self.retainment_period,
            distributions=[d.to_domain() for d in self.distributions.all()],
        )

    @classmethod
    def from_domain(cls, contract: objects.DataContract, product_id: int):
        distributions = contract.distributions
        instance, _created = cls.objects.filter(pk=contract.id).update_or_create(
            defaults={**contract.items(), "product_id": product_id}
        )
        instance.save()
        if distributions:
            instance.distributions_set.clear()
            for distribution in distributions:
                Distribution.from_domain(distribution, instance.id)
        return instance.to_domain()


class Team(models.Model):
    name = models.CharField(_("Name"), max_length=64, unique=True)
    description = models.CharField(_("Description"), max_length=512, blank=True)
    acronym = models.CharField(_("Acronym"), max_length=10, unique=True)
    po_name = models.CharField(_("Product Owner Name"), max_length=64)
    po_email = models.CharField(
        _("Product Owner Email"), max_length=64, validators=[EmailValidator]
    )
    contact_email = models.CharField(
        _("Contact E-mail"), max_length=64, validators=[EmailValidator]
    )
    scope = models.CharField(_("Scope (Entra Group)"), max_length=64)

    def __str__(self):
        return f"{self.name} ({self.acronym})"

    def to_domain(self):
        return objects.Team(
            id=self.id,
            name=self.name,
            description=self.description,
            acronym=self.acronym,
            po_name=self.po_name,
            po_email=self.po_email,
            contact_email=self.contact_email,
            scope=self.scope,
        )

    @classmethod
    def from_domain(cls, team: objects.Team):
        instance, _created = cls.objects.filter(pk=team.id).update_or_create(defaults=team.items())
        return instance.to_domain()


class Distribution(models.Model):
    access_service = models.OneToOneField(
        "DataService", on_delete=models.CASCADE, related_name="distribution", null=True
    )
    access_url = models.URLField(
        _("Access URL"), null=True, blank=True, help_text="Toegangslink naar de distributie."
    )
    download_url = models.URLField(
        _("Download URL"),
        null=True,
        blank=True,
        help_text="Link naar het bestand dat opgeslagen is binnen de omgeving van het "
        "Datateam op het Dataplatform",
    )
    contract = models.ForeignKey(
        DataContract, related_name="distributions", on_delete=models.CASCADE
    )
    format = models.CharField(
        _("Bestandstype"),
        max_length=10,
        blank=True,
        null=True,
        help_text="Het bestandsformaat: CSV, CAD, etc.",
    )

    type = models.CharField(choices=enums.DistributionType.choices(), null=True)
    refresh_period = models.CharField(
        _("Ververstermijn"),
        max_length=64,
        null=True,
        blank=True,
        help_text="Om de hoeveel tijd de data in het Data Product ververst wordt",
    )

    def __str__(self):
        return f"{self.type}"

    def to_domain(self):
        return objects.Distribution(
            id=self.id,
            access_service_id=self.access_service_id,
            access_url=self.access_url,
            download_url=self.download_url,
            format=self.format,
            type=self.type,
            refresh_period=self.refresh_period,
        )

    @classmethod
    def from_domain(cls, distribution: objects.Distribution, contract_id: int):
        instance, _created = cls.objects.filter(pk=distribution.id).update_or_create(
            defaults={**distribution.items(), "contract_id": contract_id}
        )
        return instance.id


class DataService(models.Model):
    type = models.CharField(
        _("API Type"),
        choices=enums.DataServiceType.choices(),
        max_length=10,
        help_text="Soort API: REST, atom, etc.",
        blank=True,
        null=True,
    )
    endpoint_url = models.URLField(_("API Link (Intern)"))
    product: Product = models.ForeignKey(
        "Product",
        on_delete=models.CASCADE,
        help_text="Het Product waar deze service bij hoort",
        related_name="services",
    )

    def __str__(self):
        return f"{self.type}: {self.url}"

    def to_domain(self):
        return objects.DataService(id=self.id, type=self.type, endpoint_url=self.endpoint_url)

    @classmethod
    def from_domain(cls, service: objects.DataService, product_id: int):
        cls.objects.filter(pk=service.id).update_or_create(
            defaults={**service.items(), "product_id": product_id}
        )
