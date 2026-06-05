from __future__ import annotations

from django.contrib.postgres.fields import ArrayField
from django.core.validators import EmailValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from domain.product import enums, objects
from domain.team import Team as DomainTeam


class Product(models.Model):
    contracts: models.Manager[DataContract]
    services: models.Manager[DataService]
    sinks: models.Manager[Product]

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
    other_identifier = models.CharField(
        _("Overige identifier"),
        max_length=128,
        blank=True,
        null=True,
        help_text="Een alternatieve identifier voor het Product",
    )
    type = models.CharField(
        _("Product type"),
        max_length=1,
        choices=enums.ProductType.choices(),
        null=True,
        blank=True,
    )
    themes = ArrayField(
        models.CharField(_("Thema('s)"), max_length=32, choices=enums.Theme.choices()),
        null=True,
        blank=True,
        help_text="Thema's voor Data Producten zoals gedefinieerd als de thema's op nationaal "
        "niveau. Dit geeft de mogelijkheid om te koppelen op de nationale repository.",
    )
    team = models.ForeignKey["Team"](
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
    data_steward = models.CharField(
        _("Business Data Steward"),
        blank=True,
        null=True,
        help_text="Contact E-mail adres van de verantwoordelijke Data Steward in de business",
        validators=[EmailValidator()],
    )
    _contact_email = models.CharField(
        _("Contact Email"),
        max_length=128,
        null=True,
        blank=True,
        help_text="Contact E-mail adres van het team",
        validators=[EmailValidator()],
    )
    publication_status = models.CharField(
        _("Publicatiestatus"),
        max_length=1,
        choices=enums.PublicationStatus.choices(),
        null=True,
        blank=True,
    )
    publication_date = models.DateTimeField(
        _("Publicatiedatum"),
        blank=True,
        null=True,
        help_text="Datum waarop het Data Product voor het eerst is gepubliceerd.",
    )
    refresh_period = models.JSONField(
        _("Ververstermijn"),
        null=True,
        default=dict,
        help_text='De ververstermijn in de vorm {"frequency": int, "unit": periodString}, '
        'waarbij periodStr iets is als "uur", "dag", "week", "maand", "jaar"',
    )
    last_updated = models.DateTimeField(auto_now=True)
    last_editor = models.CharField(
        _("Last Editor"),
        null=True,
        blank=True,
        default="import",
        help_text="De gebruiker of systeem account die de update doet",
    )
    created_at = models.DateTimeField(auto_now_add=True)

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
    endorsement = models.CharField(
        _("Endorsement niveau"),
        max_length=1,
        choices=enums.EndorsementLevel.choices(),
        null=True,
        blank=True,
        help_text="Het endorsement niveau van het Informatieproduct.",
    )
    sources = models.ManyToManyField("self", symmetrical=False, related_name="sinks")

    def __str__(self):
        return self.name or str(self.pk)

    @property
    def contact_email(self):
        return self._contact_email or self.team.contact_email

    @contact_email.setter
    def contact_email(self, value):
        if value and value != self.team.contact_email:
            self._contact_email = value
        else:
            self._contact_email = None

    @property
    def owner(self):
        return self._owner or self.team.po_name

    @owner.setter
    def owner(self, value):
        if value and value != self.team.po_name:
            self._owner = value
        else:
            self._owner = None

    def to_domain(self, published_only: bool = False):
        if published_only and self.publication_status != enums.PublicationStatus.PUBLISHED.value:
            return None
        contracts = [c.to_domain() for c in self.contracts.order_by("id")]
        if published_only:
            contracts = [
                c
                for c in contracts
                if c.publication_status == enums.PublicationStatus.PUBLISHED.value
            ]
        return objects.Product(
            id=self.pk,
            has_revision=hasattr(self, "revision"),
            type=self.type,
            name=self.name,
            description=self.description,
            other_identifier=self.other_identifier,
            team_id=self.team.pk,
            language=self.language,
            is_geo=self.is_geo,
            schema_url=self.schema_url,
            contracts=contracts,
            themes=self.themes,
            last_updated=self.last_updated,
            last_editor=self.last_editor,
            created_at=self.created_at,
            refresh_period=(
                objects.RefreshPeriod.from_string(self.refresh_period)
                if self.refresh_period
                else None
            ),
            publication_status=self.publication_status,
            publication_date=self.publication_date,
            owner=self.owner,
            contact_email=self.contact_email,
            data_steward=self.data_steward,
            endorsement=self.endorsement,
            services=[s.to_domain() for s in self.services.order_by("id")],
            sources=list(self.sources.values_list("pk", flat=True)),
            sinks=list(self.sinks.values_list("pk", flat=True)),
        )

    @classmethod
    def from_domain(cls, product: objects.Product):
        instance, _created = cls.objects.filter(pk=product.id).update_or_create(
            defaults=product.items()
        )
        instance.owner = product.owner
        instance.refresh_period = (
            product.refresh_period.to_string if product.refresh_period is not None else None
        )
        instance.save()

        # Create/update services
        to_delete = instance.services.all()
        for service in product.services or []:
            service_id = DataService.from_domain(service, instance.pk)
            to_delete = to_delete.exclude(pk=service_id)
        to_delete.delete()

        # Create/update contracts
        to_delete = instance.contracts.all()
        for contract in product.contracts or []:
            contract = DataContract.from_domain(contract, instance.pk)
            to_delete = to_delete.exclude(pk=contract.id)
        to_delete.delete()

        instance.refresh_from_db()
        return instance.to_domain()


class ProductRevision(models.Model):
    team_id: int

    product = models.OneToOneField(
        Product,
        on_delete=models.CASCADE,
        related_name="revision",
    )
    team = models.ForeignKey(
        "Team",
        on_delete=models.CASCADE,
        related_name="product_revisions",
    )
    name = models.CharField(max_length=64, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    other_identifier = models.CharField(max_length=128, blank=True, null=True)
    language = models.CharField(
        choices=enums.Language.choices(),
        null=True,
        blank=True,
    )
    is_geo = models.BooleanField(blank=True, null=True)
    schema_url = models.URLField(blank=True, null=True)
    type = models.CharField(
        max_length=1,
        choices=enums.ProductType.choices(),
        null=True,
        blank=True,
    )
    themes = ArrayField(
        models.CharField(max_length=32, choices=enums.Theme.choices()),
        null=True,
        blank=True,
    )
    _owner = models.CharField(max_length=64, null=True, blank=True)
    data_steward = models.CharField(
        blank=True,
        null=True,
        validators=[EmailValidator()],
    )
    _contact_email = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        validators=[EmailValidator()],
    )
    refresh_period = models.JSONField(null=True, default=dict)
    last_updated = models.DateTimeField(auto_now=True)
    last_editor = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        default="import",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    base_last_updated = models.DateTimeField()
    endorsement = models.CharField(
        max_length=1,
        choices=enums.EndorsementLevel.choices(),
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.name or str(self.pk)

    @property
    def contact_email(self):
        return self._contact_email or self.team.contact_email

    @contact_email.setter
    def contact_email(self, value):
        if value and value != self.team.contact_email:
            self._contact_email = value
        else:
            self._contact_email = None

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
        domain_product = self.product.to_domain()
        domain_product.update_from_dict(
            {
                "name": self.name,
                "description": self.description,
                "other_identifier": self.other_identifier,
                "language": self.language,
                "is_geo": self.is_geo,
                "schema_url": self.schema_url,
                "type": self.type,
                "team_id": self.team_id,
                "themes": self.themes,
                "last_updated": self.last_updated,
                "last_editor": self.last_editor,
                "refresh_period": (
                    objects.RefreshPeriod.from_string(self.refresh_period)
                    if self.refresh_period
                    else None
                ),
                "owner": self.owner,
                "contact_email": self.contact_email,
                "data_steward": self.data_steward,
                "endorsement": self.endorsement,
            }
        )
        return domain_product

    @classmethod
    def from_domain(cls, product: objects.Product):
        if product.id is None:
            raise ValueError("Product revision requires a persisted product id.")

        live_product = Product.objects.select_related("team").get(pk=product.id)
        instance = cls.objects.filter(product=live_product).first()
        if instance is None:
            instance = cls(product=live_product, base_last_updated=live_product.last_updated)

        instance.team_id = product.team_id
        instance.name = product.name
        instance.description = product.description
        instance.other_identifier = product.other_identifier
        instance.language = product.language
        instance.is_geo = product.is_geo
        instance.schema_url = product.schema_url
        instance.type = product.type
        instance.themes = product.themes
        instance.refresh_period = (
            product.refresh_period.to_string if product.refresh_period is not None else None
        )
        instance.last_editor = product.last_editor
        instance.data_steward = product.data_steward
        instance.endorsement = product.endorsement
        instance.owner = product.owner
        instance.contact_email = product.contact_email
        instance.save()
        return instance.to_domain()


class DataContract(models.Model):
    distributions: models.Manager[Distribution]

    product = models.ForeignKey[Product](
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
    publication_status = models.CharField(
        _("Publicatiestatus"),
        max_length=1,
        blank=True,
        null=True,
        choices=enums.PublicationStatus.choices(),
    )
    publication_date = models.DateTimeField(
        _("Publicatiedatum"),
        blank=True,
        null=True,
        help_text="Datum waarop het Data Contract voor het eerst is gepubliceerd.",
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
    privacy_level = models.CharField(
        _("Privacyniveau"),
        choices=enums.PrivacyLevel.choices(),
        null=True,
        blank=True,
        help_text="Het privacyniveau van het contract",
    )
    last_updated = models.DateTimeField(auto_now=True)
    last_editor = models.CharField(
        _("Last Editor"),
        null=True,
        blank=True,
        default="import",
        help_text="De gebruiker of systeem account die de update doet",
    )
    created_at = models.DateTimeField(auto_now_add=True)

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
    scopes = ArrayField(
        models.CharField(_("Scopes"), max_length=64),
        null=True,
        blank=True,
        help_text="De scope ids die gebruiken moet hebben om dit contract te kunnen afnemen.",
    )
    tables = ArrayField(
        models.CharField(_("Tabellen"), max_length=64),
        null=True,
        blank=True,
        help_text="De ids van de tabellen binnen de dataset die onder dit contract vallen. "
        "Laat leeg om alle tabellen op te nemen.",
    )

    def __str__(self):
        return self.name or str(self.pk)

    @property
    def schema_url(self) -> str | None:
        if self.product.schema_url:
            base_url = self.product.schema_url
        if self.scopes:
            scopes = ",".join(self.scopes)
        if self.tables:
            tables = ",".join(self.tables)

        if self.product.schema_url and self.scopes and self.tables:
            return f"{base_url}?scopes={scopes}&tables={tables}"
        elif self.product.schema_url and self.scopes:
            return f"{base_url}?scopes={scopes}"
        else:
            return None

    def to_domain(self):
        return objects.DataContract(
            id=self.pk,
            has_revision=hasattr(self, "revision"),
            publication_status=self.publication_status,
            publication_date=self.publication_date,
            purpose=self.purpose,
            name=self.name,
            last_updated=self.last_updated,
            last_editor=self.last_editor,
            privacy_level=self.privacy_level,
            scopes=self.scopes,
            confidentiality=self.confidentiality,
            start_date=self.start_date,
            retainment_period=self.retainment_period,
            distributions=[d.to_domain() for d in self.distributions.order_by("id")],
            tables=self.tables,
            schema_url=self.schema_url,
        )

    @classmethod
    def from_domain(cls, contract: objects.DataContract, product_id: int):
        instance, _created = cls.objects.filter(pk=contract.id).update_or_create(
            defaults={**contract.items(), "product_id": product_id}
        )
        # Handle distributions, they may potentially all be deleted:
        to_delete = instance.distributions.all()
        for distribution in contract.distributions or []:
            distro_id = Distribution.from_domain(distribution, instance.pk)
            # Exclude the distribution that still exists.
            to_delete = to_delete.exclude(pk=distro_id)
        to_delete.delete()
        return instance.to_domain()


class DataContractRevision(models.Model):
    distributions: models.Manager[DataContractRevisionDistribution]

    contract = models.OneToOneField(
        DataContract,
        on_delete=models.CASCADE,
        related_name="revision",
    )
    name = models.CharField(max_length=64, blank=True, null=True)
    purpose = models.TextField(blank=True, null=True)
    privacy_level = models.CharField(
        choices=enums.PrivacyLevel.choices(),
        null=True,
        blank=True,
    )
    last_updated = models.DateTimeField(auto_now=True)
    last_editor = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        default="import",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    confidentiality = models.CharField(
        choices=enums.ConfidentialityLevel.choices(),
        blank=True,
        null=True,
    )
    retainment_period = models.IntegerField(blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    scopes = ArrayField(models.CharField(max_length=64), null=True, blank=True)
    tables = ArrayField(models.CharField(max_length=64), null=True, blank=True)
    base_last_updated = models.DateTimeField()
    has_distribution_draft = models.BooleanField(default=False)

    def __str__(self):
        return self.name or str(self.pk)

    @property
    def schema_url(self) -> str | None:
        if self.contract.product.schema_url:
            base_url = self.contract.product.schema_url
        if self.scopes:
            scopes = ",".join(self.scopes)
        if self.tables:
            tables = ",".join(self.tables)

        if self.contract.product.schema_url and self.scopes and self.tables:
            return f"{base_url}?scopes={scopes}&tables={tables}"
        elif self.contract.product.schema_url and self.scopes:
            return f"{base_url}?scopes={scopes}"
        else:
            return None

    def to_domain(self):
        domain_contract = self.contract.to_domain()
        domain_contract.update_from_dict(
            {
                "name": self.name,
                "purpose": self.purpose,
                "privacy_level": self.privacy_level,
                "last_updated": self.last_updated,
                "last_editor": self.last_editor,
                "confidentiality": self.confidentiality,
                "retainment_period": self.retainment_period,
                "start_date": self.start_date,
                "scopes": self.scopes,
                "tables": self.tables,
                "schema_url": self.schema_url,
            }
        )
        if self.has_distribution_draft:
            domain_contract.distributions = [
                distribution.to_domain()
                for distribution in self.distributions.select_related(
                    "live_distribution"
                ).order_by("id")
            ]
        return domain_contract

    @classmethod
    def from_domain(cls, contract: objects.DataContract, product_id: int):
        if contract.id is None:
            raise ValueError("Contract revision requires a persisted contract id.")

        live_contract = DataContract.objects.select_related("product").get(
            pk=contract.id,
            product_id=product_id,
        )
        instance = cls.objects.filter(contract=live_contract).first()
        if instance is None:
            instance = cls(contract=live_contract, base_last_updated=live_contract.last_updated)

        instance.name = contract.name
        instance.purpose = contract.purpose
        instance.privacy_level = contract.privacy_level
        instance.last_editor = contract.last_editor
        instance.confidentiality = contract.confidentiality
        instance.retainment_period = contract.retainment_period
        instance.start_date = contract.start_date
        instance.scopes = contract.scopes
        instance.tables = contract.tables
        instance.has_distribution_draft = True
        instance.save()

        live_distributions_by_id = {
            distribution.pk: distribution
            for distribution in live_contract.distributions.all().order_by("id")
        }
        draft_distribution_ids = set()
        for distribution in contract.distributions or []:
            revision_distribution = DataContractRevisionDistribution.from_domain(
                distribution=distribution,
                revision=instance,
                live_distribution=live_distributions_by_id.get(distribution.id),
            )
            draft_distribution_ids.add(revision_distribution.pk)

        instance.distributions.exclude(pk__in=draft_distribution_ids).delete()
        return instance.to_domain()


class DataContractRevisionDistribution(models.Model):
    live_distribution_id: int | None

    revision = models.ForeignKey(
        DataContractRevision,
        on_delete=models.CASCADE,
        related_name="distributions",
    )
    live_distribution = models.OneToOneField(
        "Distribution",
        on_delete=models.SET_NULL,
        related_name="revision_copy",
        null=True,
        blank=True,
    )
    access_service_id = models.IntegerField(null=True, blank=True)
    access_url = models.URLField(
        _("Access URL"),
        null=True,
        blank=True,
        help_text="Toegangslink naar de distributie.",
    )
    download_url = models.URLField(
        _("Download URL"),
        null=True,
        blank=True,
        help_text="Link naar het bestand dat opgeslagen is binnen de omgeving van het "
        "Datateam op het Dataplatform",
    )
    format = models.CharField(
        _("Bestandstype"),
        max_length=10,
        blank=True,
        null=True,
        help_text="Het bestandsformaat: CSV, CAD, etc.",
    )
    filename = models.CharField(
        _("Bestandsnaam"),
        max_length=255,
        blank=True,
        null=True,
        help_text="De naam van het bestand.",
    )
    type = models.CharField(choices=enums.DistributionType.choices(), null=True, blank=True)
    refresh_period = models.CharField(
        _("Ververstermijn"),
        max_length=64,
        null=True,
        blank=True,
        help_text="Om de hoeveel tijd de data in het Data Product ververst wordt",
    )
    crs = ArrayField(
        models.CharField(
            _("Geo coördinaatreferentiesysteem"),
            choices=enums.CoordRefSystem.choices(upper=True),
        ),
        blank=True,
        null=True,
        help_text="Geo-informatie is direct gekoppeld aan een locatie op aarde. De manier waarop "
        "die koppeling wordt gelegd, wordt beschreven in het coördinaatreferentiesysteem (CRS). "
        "Hierin worden coördinaten van een locatie vastgelegd. Een distributie kan meerdere "
        "CRS'en ondersteunen.",
    )

    def __str__(self):
        return str(self.live_distribution_id or self.pk)

    def to_domain(self):
        return objects.Distribution(
            id=self.live_distribution_id or -self.pk,
            access_service_id=self.access_service_id,
            access_url=self.access_url,
            download_url=self.download_url,
            format=self.format,
            filename=self.filename,
            type=self.type,
            refresh_period=(
                objects.RefreshPeriod.from_string(self.refresh_period)
                if self.refresh_period
                else None
            ),
            crs=[enums.CoordRefSystem[crs] for crs in self.crs] if self.crs else None,
        )

    @classmethod
    def from_domain(
        cls,
        *,
        distribution: objects.Distribution,
        revision: DataContractRevision,
        live_distribution: Distribution | None,
    ):
        instance = None
        if live_distribution is not None:
            instance = cls.objects.filter(
                revision=revision,
                live_distribution=live_distribution,
            ).first()
        elif distribution.id is not None and distribution.id < 0:
            instance = cls.objects.filter(
                revision=revision,
                pk=abs(distribution.id),
                live_distribution__isnull=True,
            ).first()

        if instance is None:
            instance = cls(revision=revision, live_distribution=live_distribution)

        instance.access_service_id = distribution.access_service_id
        instance.access_url = distribution.access_url
        instance.download_url = distribution.download_url
        instance.format = distribution.format
        instance.filename = distribution.filename
        instance.type = distribution.type
        instance.refresh_period = (
            distribution.refresh_period.to_string if distribution.refresh_period else None
        )
        instance.crs = (
            [crs.value if hasattr(crs, "value") else crs for crs in distribution.crs]
            if distribution.crs
            else None
        )
        instance.save()
        return instance


class Team(models.Model):
    products: models.Manager[Product]
    name = models.CharField(_("Name"), max_length=128, unique=True)
    description = models.CharField(_("Description"), max_length=512, blank=True, null=True)
    acronym = models.CharField(_("Acronym"), max_length=10, unique=True)
    po_name = models.CharField(_("Product Owner Name"), max_length=64)
    po_email = models.CharField(
        _("Product Owner Email"), max_length=64, validators=[EmailValidator()]
    )
    contact_email = models.CharField(
        _("Contact E-mail"), max_length=64, validators=[EmailValidator()]
    )
    scope = models.CharField(_("Scope (Entra Group)"), max_length=64)

    def __str__(self):
        return f"{self.name} ({self.acronym})"

    def to_domain(self) -> DomainTeam:
        return DomainTeam(
            id=self.pk,
            name=self.name,
            description=self.description,
            acronym=self.acronym,
            po_name=self.po_name,
            po_email=self.po_email,
            contact_email=self.contact_email,
            scope=self.scope,
            product_count=self.products.filter(publication_status__in=["P", "I"]).count(),
        )

    @classmethod
    def from_domain(cls, team: DomainTeam) -> DomainTeam:
        instance, _created = cls.objects.filter(pk=team.id).update_or_create(defaults=team.items())
        return instance.to_domain()


class Distribution(models.Model):
    access_service_id: int

    access_service = models.OneToOneField(
        "DataService", on_delete=models.CASCADE, related_name="distribution", null=True
    )
    access_url = models.URLField(
        _("Access URL"),
        null=True,
        blank=True,
        help_text="Toegangslink naar de distributie.",
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
    filename = models.CharField(
        _("Bestandsnaam"),
        max_length=255,
        blank=True,
        null=True,
        help_text="De naam van het bestand.",
    )
    type = models.CharField(choices=enums.DistributionType.choices(), null=True, blank=True)
    refresh_period = models.CharField(
        _("Ververstermijn"),
        max_length=64,
        null=True,
        blank=True,
        help_text="Om de hoeveel tijd de data in het Data Product ververst wordt",
    )
    crs = ArrayField(
        models.CharField(
            _("Geo coördinaatreferentiesysteem"),
            choices=enums.CoordRefSystem.choices(upper=True),
        ),
        blank=True,
        null=True,
        help_text="Geo-informatie is direct gekoppeld aan een locatie op aarde. De manier waarop "
        "die koppeling wordt gelegd, wordt beschreven in het coördinaatreferentiesysteem (CRS). "
        "Hierin worden coördinaten van een locatie vastgelegd. Een distributie kan meerdere "
        "CRS'en ondersteunen.",
    )

    def __str__(self):
        return f"{self.type}"

    def to_domain(self):
        return objects.Distribution(
            id=self.pk,
            access_service_id=self.access_service_id,
            access_url=self.access_url,
            download_url=self.download_url,
            format=self.format,
            filename=self.filename,
            type=self.type,
            refresh_period=(
                objects.RefreshPeriod.from_string(self.refresh_period)
                if self.refresh_period
                else None
            ),
            crs=[enums.CoordRefSystem[crs] for crs in self.crs] if self.crs else None,
        )

    @classmethod
    def from_domain(cls, distribution: objects.Distribution, contract_id: int):
        instance, _created = cls.objects.filter(pk=distribution.id).update_or_create(
            defaults={**distribution.items(), "contract_id": contract_id}
        )
        instance.refresh_period = (
            distribution.refresh_period.to_string if distribution.refresh_period else None
        )
        instance.save()
        return instance.pk


class DataService(models.Model):
    type = models.CharField(
        _("API Type"),
        choices=enums.DataServiceType.choices(),
        max_length=10,
        help_text="Soort API: REST, atom, etc.",
        blank=True,
        null=True,
    )
    endpoint_url = models.URLField(_("API Link (Intern)"), null=True, blank=True)
    product = models.ForeignKey[Product](
        "Product",
        on_delete=models.CASCADE,
        help_text="Het Product waar deze service bij hoort",
        related_name="services",
    )

    def __str__(self):
        return f"{self.type}: {self.endpoint_url}"

    def to_domain(self):
        return objects.DataService(id=self.pk, type=self.type, endpoint_url=self.endpoint_url)

    @classmethod
    def from_domain(cls, service: objects.DataService, product_id: int):
        instance, _created = cls.objects.filter(pk=service.id).update_or_create(
            defaults={**service.items(), "product_id": product_id}
        )
        return instance.pk
