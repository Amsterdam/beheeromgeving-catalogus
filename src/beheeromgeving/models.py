from __future__ import annotations

from django.contrib.postgres.fields import ArrayField
from django.core.validators import EmailValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class DataContract(models.Model):
    name = models.CharField(
        _("Naam"),
        unique=True,
        max_length=64,
        help_text="De naam van het Data Product. Deze moet uniek zijn",
    )
    description = models.TextField(
        _("Beschrijving"),
        help_text="Beschrijving en betekenis van het Data Product",
    )
    purpose = models.TextField(
        _("Doelbinding"),
        help_text="Beschrijf hier de doelbinding aan de hand van de use-case(s) waarvoor dit Data"
        " Product is bedoeld en zijn bestaansrecht aan ontleent. Het uitgangspunt van doelbinding"
        " is, dat gegevens worden verwerkt en verzameld voor een welbepaald, uitdrukkelijk "
        "omschreven en gerechtvaardigde doel. 'Welbepaald en uitdrukkelijk omschreven' houdt in "
        "dat men geen gegevens mag verzamelen zonder een precieze doelomschrijving",
    )
    THEME_CHOICES = (
        ("B", "Bestuur"),
        ("CR", "Cultuur en recreatie"),
        ("E", "Economie"),
        ("F", "Financiën"),
        ("H", "Huisvesting"),
        ("I", "Internationaal"),
        ("L", "Landbouw"),
        ("MI", "Migratie en integratie"),
        ("NM", "Natuur en milieu"),
        ("OW", "Onderwijs en wetenschap"),
        ("OOV", "Openbare orde en veiligheid"),
        ("R", "Recht"),
        ("RI", "Ruimte en infrastructuur"),
        ("SZ", "Sociale zekerheid"),
        ("V", "Verkeer"),
        ("W", "Werk"),
        ("ZG", "Zorg en gezondheid"),
    )
    themes = ArrayField(
        models.CharField(
            _("Thema('s)"),
            max_length=32,
            choices=THEME_CHOICES,
        ),
        help_text="Thema's voor Data Producten zoals gedefinieerd als de thema's op nationaal "
        "niveau. Dit geeft de mogelijkheid om te koppelen op de nationale repository.",
    )
    tags = ArrayField(
        models.CharField(_("Zoekwoorden"), max_length=32),
        help_text="Zoekwoorden of Tags die het Data Product of zijn inhoud beschrijven. Dit is "
        "bedoeld om de vindbaarheid in de Data Catalogus te ondersteunen. Het gaat om een "
        "logische groepering van Data Producten. De lijst met toegestane waarden wordt beheerd "
        "door het Data Platform",
    )
    datateam: DataTeam = models.ForeignKey(
        "DataTeam",
        on_delete=models.CASCADE,
        help_text="Het Datateam verantwoordelijk voor en gekoppeld aan het Data Product",
    )
    _owner = models.CharField(
        _("Eigenaar"),
        max_length=64,
        null=True,
        help_text="De eigenaar van het Data Product. Standaard is dit de Product Owner van het "
        "betreffende Datateam, tenzij anders overeengekomen. Pas in dat geval de waarde aan",
    )
    data_steward = models.CharField(
        _("Business Data Steward"),
        null=True,
        help_text="Contact E-mail adres van de verantwoordelijke Data Steward in de business",
        validators=[EmailValidator],
    )
    LANGUAGE_CHOICES = (("NL", "Nederlands"), ("EN", "English"))
    language = models.CharField(
        _("Taal"),
        choices=LANGUAGE_CHOICES,
        help_text="De gebruikte taal in de inhoud van het Data Product",
    )
    CONFIDENTIALITY_CHOICES = (
        ("Openbaar", "Openbaar"),
        ("Intern", "Intern"),
        ("Vertrouwelijk", "Vertrouwelijk"),
        ("Geheim", "Geheim"),
    )
    confidentiality = models.CharField(
        _("Vertrouwelijkheidsniveau"),
        choices=CONFIDENTIALITY_CHOICES,
        help_text="Het niveau van vertrouwelijkheid van de data in het Data Product. Vereiste "
        "voor BBN",
    )
    PRIVACY_CHOICES = (
        ("NPI", "Niet persoonlijk identificeerbaar"),
        ("PI", "Persoonlijk identificeerbaar"),
        ("BI", "Bijzonder identificeerbaar"),
    )
    privacy = models.CharField(
        _("Privacyniveau"),
        choices=PRIVACY_CHOICES,
        help_text="Het privacyniveau van het totale Data Product",
    )
    is_geo = models.BooleanField(
        _("Geo Data"),
        help_text="Of het Data Product al dan niet geografische data bevat",
    )
    CRS_CHOICES = (
        ("RD", "RD"),
        ("ETRS89", "ETRS89"),
        ("WGS84", "WGS84"),
        ("UTM35S", "UTM35S"),
        ("NVT", "Niet van toepassing"),
    )
    crs = models.CharField(
        _("Geo coördinaatreferentiesysteem"),
        choices=CRS_CHOICES,
        help_text="Geo-informatie is direct gekoppeld aan een locatie op aarde. De manier waarop "
        "die koppeling wordt gelegd, wordt beschreven in het coördinaatreferentiesysteem (CRS). "
        "Hierin worden coördinaten van een locatie vastgelegd",
    )
    refresh_period = models.CharField(
        _("Ververstermijn"),
        max_length=64,
        help_text="Om de hoeveel tijd de data in het Data Product ververst wordt",
    )
    retainment_period = models.IntegerField(
        _("Bewaartermijn in maanden"),
        help_text="Om te voldoen aan de duurzame toegankelijkheidseisen (DUTO) van de overheid is "
        "het nodig om een bewaartermijn vast te leggen voor Data Producten zodat het Datateam hun "
        "omgeving hierop kan inrichten en de data te verwijderen wanneer dat nodig is",
    )
    start_date = models.DateField(
        _("Startdatum Contract"),
        help_text="Datum waarop het Datacontract ingaat, en dus actief wordt. Deze datum kan in de"
        " toekomst liggen en kan een andere datum zijn dan de aanmaak datum van het Data Product. "
        "Dit is van belang wanneer er een nieuwe versie van het datacontract wordt gemaakt. Dit is"
        " geen systeemveld (zoals Aanmaak -en Wijzigingsdatum) en moet daarom separaat worden "
        "opgegeven. Wanneer het de innitiele versie van het Data Product betreft, vul hier dan de "
        "aanmaakdatum van het contract in. Wanneer het Data Product gemigreerd is vanaf de oude "
        "Data Catalogus, vul hier dan de publicatiedatum van de oude catalogus (Issued) in.",
    )
    schema = models.JSONField(
        _("Schema"),
        null=True,
        default=dict,
        help_text="Het schema in JSON formaat of handmatig via dit veld. Het schema is nodig voor "
        "de koppeling met het Data Product. Als je gebruik maakt van Amsterdam Schema en je wilt "
        "daarnaar verwijzen, vul dan het 'Amsterdam Schema Dataset Verwijzing' veld in en maak dit"
        " veld een leeg object ({})",
    )
    schema_url = models.URLField(
        _("Amsterdam Schema Dataproduct verwijzing (url)"),
        null=True,
        help_text="Verwijzing naar een dataset beschreven in Amsterdam Schema. Dit is alleen een "
        "vervanging voor het schema, niet de rest van het Data Contract. Als het 'Schema' veld is "
        "ingevuld en je geen gebruik maakt van Amsterdam Schema, dan blijft dit veld leeg",
    )
    distribution = models.OneToOneField("Distribution", on_delete=models.CASCADE)
    version = models.CharField(
        _("Versie"),
        max_length=4,
        help_text="Het versienummer van het Data Product zoals bijgehouden door het Datateam",
    )

    def __str__(self):
        return f"DataContract: {self.name}"

    @property
    def owner(self):
        return self._owner or self.datateam.product_owner

    @owner.setter
    def owner(self, value):
        if value:
            self._owner = value
        else:
            self._owner = None

    @property
    def contact_email(self):
        return self.datateam.contact_email


class DataTeam(models.Model):
    name = models.CharField(_("Name"), max_length=64, unique=True)
    acronym = models.CharField(_("Acronym"), max_length=10, unique=True)
    product_owner = models.CharField(_("Product Owner"), max_length=64)
    contact_email = models.CharField(
        _("Contact E-mail"), max_length=64, validators=[EmailValidator]
    )

    def __str__(self):
        return f"DataTeam: {self.name} ({self.acronym})"


class Distribution(models.Model):
    table = models.BooleanField(_("Heeft Tabel distributie"), default=False)

    def __str__(self):
        return f"Distribution {self.id}"


class APIDistribution(models.Model):
    distribution = models.ForeignKey(Distribution, on_delete=models.CASCADE, related_name="apis")
    api_type = models.CharField(
        _("API Type"), max_length=10, help_text="Soort API: REST, atom, etc."
    )
    url = models.URLField(_("API Link (Intern)"))

    def __str__(self):
        return f"APIDistribution {self.id}: {self.url}"


class FileDistribution(models.Model):
    distribution = models.ForeignKey(Distribution, on_delete=models.CASCADE, related_name="files")
    file_format = models.CharField(
        _("Bestandstype"),
        max_length=10,
        help_text="Het bestandsformaat: CSV, CAD, etc.",
    )
    link = models.TextField(
        _("Bestand Link (Intern)"),
        help_text="Link naar het bestand dat opgeslagen is binnen de omgeving van het "
        "Datateam op het Dataplatform",
    )

    def __str__(self):
        return f"FileDistribution {self.id}: {self.link}"
