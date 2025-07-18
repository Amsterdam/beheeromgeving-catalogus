# Generated by Django 5.2.3 on 2025-06-25 11:09

import django.contrib.postgres.fields
import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="DataTeam",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("name", models.CharField(max_length=64, unique=True, verbose_name="Name")),
                ("acronym", models.CharField(max_length=10, unique=True, verbose_name="Acronym")),
                ("product_owner", models.CharField(max_length=64, verbose_name="Product Owner")),
                (
                    "contact_email",
                    models.CharField(
                        max_length=64,
                        validators=[django.core.validators.EmailValidator],
                        verbose_name="Contact E-mail",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Distribution",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "table",
                    models.BooleanField(default=False, verbose_name="Heeft Tabel distributie"),
                ),
            ],
        ),
        migrations.CreateModel(
            name="DataContract",
            fields=[
                (
                    "name",
                    models.CharField(
                        help_text="De naam van het Data Product. Deze moet uniek zijn",
                        max_length=64,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                        verbose_name="Naam",
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        help_text="Beschrijving en betekenis van het Data Product",
                        verbose_name="Beschrijving",
                    ),
                ),
                (
                    "purpose",
                    models.TextField(
                        help_text="Beschrijf hier de doelbinding aan de hand van de use-case(s) waarvoor dit Data Product is bedoeld en zijn bestaansrecht aan ontleent. Het uitgangspunt van doelbinding is, dat gegevens worden verwerkt en verzameld voor een welbepaald, uitdrukkelijk omschreven en gerechtvaardigde doel. 'Welbepaald en uitdrukkelijk omschreven' houdt in dat men geen gegevens mag verzamelen zonder een precieze doelomschrijving",
                        verbose_name="Doelbinding",
                    ),
                ),
                (
                    "themes",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.CharField(
                            choices=[
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
                            ],
                            max_length=32,
                            verbose_name="Thema('s)",
                        ),
                        help_text="Thema's voor Data Producten zoals gedefinieerd als de thema's op nationaal niveau. Dit geeft de mogelijkheid om te koppelen op de nationale repository.",
                        size=None,
                    ),
                ),
                (
                    "tags",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.CharField(max_length=32, verbose_name="Zoekwoorden"),
                        help_text="Zoekwoorden of Tags die het Data Product of zijn inhoud beschrijven. Dit is bedoeld om de vindbaarheid in de Data Catalogus te ondersteunen. Het gaat om een logische groepering van Data Producten. De lijst met toegestane waarden wordt beheerd door het Data Platform",
                        size=None,
                    ),
                ),
                (
                    "_owner",
                    models.CharField(
                        help_text="De eigenaar van het Data Product. Standaard is dit de Product Owner van het betreffende Datateam, tenzij anders overeengekomen. Pas in dat geval de waarde aan",
                        max_length=64,
                        null=True,
                        verbose_name="Eigenaar",
                    ),
                ),
                (
                    "data_steward",
                    models.CharField(
                        help_text="Contact E-mail adres van de verantwoordelijke Data Steward in de business",
                        null=True,
                        validators=[django.core.validators.EmailValidator],
                        verbose_name="Business Data Steward",
                    ),
                ),
                (
                    "language",
                    models.CharField(
                        choices=[("NL", "Nederlands"), ("EN", "English")],
                        help_text="De gebruikte taal in de inhoud van het Data Product",
                        verbose_name="Taal",
                    ),
                ),
                (
                    "confidentiality",
                    models.CharField(
                        choices=[
                            ("Openbaar", "Openbaar"),
                            ("Intern", "Intern"),
                            ("Vertrouwelijk", "Vertrouwelijk"),
                            ("Geheim", "Geheim"),
                        ],
                        help_text="Het niveau van vertrouwelijkheid van de data in het Data Product. Vereiste voor BBN",
                        verbose_name="Vertrouwelijkheidsniveau",
                    ),
                ),
                (
                    "privacy",
                    models.CharField(
                        choices=[
                            ("NPI", "Niet persoonlijk identificeerbaar"),
                            ("PI", "Persoonlijk identificeerbaar"),
                            ("BI", "Bijzonder identificeerbaar"),
                        ],
                        help_text="Het privacyniveau van het totale Data Product",
                        verbose_name="Privacyniveau",
                    ),
                ),
                (
                    "is_geo",
                    models.BooleanField(
                        help_text="Of het Data Product al dan niet geografische data bevat",
                        verbose_name="Geo Data",
                    ),
                ),
                (
                    "crs",
                    models.CharField(
                        choices=[
                            ("RD", "RD"),
                            ("ETRS89", "ETRS89"),
                            ("WGS84", "WGS84"),
                            ("UTM35S", "UTM35S"),
                            ("NVT", "Niet van toepassing"),
                        ],
                        help_text="Geo-informatie is direct gekoppeld aan een locatie op aarde. De manier waarop die koppeling wordt gelegd, wordt beschreven in het coördinaatreferentiesysteem (CRS). Hierin worden coördinaten van een locatie vastgelegd",
                        verbose_name="Geo coördinaatreferentiesysteem",
                    ),
                ),
                (
                    "refresh_period",
                    models.CharField(
                        help_text="Om de hoeveel tijd de data in het Data Product ververst wordt",
                        max_length=64,
                        verbose_name="Ververstermijn",
                    ),
                ),
                (
                    "retainment_period",
                    models.IntegerField(
                        help_text="Om te voldoen aan de duurzame toegankelijkheidseisen (DUTO) van de overheid is het nodig om een bewaartermijn vast te leggen voor Data Producten zodat het Datateam hun omgeving hierop kan inrichten en de data te verwijderen wanneer dat nodig is",
                        verbose_name="Bewaartermijn in maanden",
                    ),
                ),
                (
                    "start_date",
                    models.DateField(
                        help_text="Datum waarop het Datacontract ingaat, en dus actief wordt. Deze datum kan in de toekomst liggen en kan een andere datum zijn dan de aanmaak datum van het Data Product. Dit is van belang wanneer er een nieuwe versie van het datacontract wordt gemaakt. Dit is geen systeemveld (zoals Aanmaak -en Wijzigingsdatum) en moet daarom separaat worden opgegeven. Wanneer het de innitiele versie van het Data Product betreft, vul hier dan de aanmaakdatum van het contract in. Wanneer het Data Product gemigreerd is vanaf de oude Data Catalogus, vul hier dan de publicatiedatum van de oude catalogus (Issued) in.",
                        verbose_name="Startdatum Contract",
                    ),
                ),
                (
                    "schema",
                    models.JSONField(
                        default=dict,
                        help_text="Het schema in JSON formaat of handmatig via dit veld. Het schema is nodig voor de koppeling met het Data Product. Als je gebruik maakt van Amsterdam Schema en je wilt daarnaar verwijzen, vul dan het 'Amsterdam Schema Dataset Verwijzing' veld in en maak dit veld een leeg object ({})",
                        null=True,
                        verbose_name="Schema",
                    ),
                ),
                (
                    "schema_url",
                    models.URLField(
                        help_text="Verwijzing naar een dataset beschreven in Amsterdam Schema. Dit is alleen een vervanging voor het schema, niet de rest van het Data Contract. Als het 'Schema' veld is ingevuld en je geen gebruik maakt van Amsterdam Schema, dan blijft dit veld leeg",
                        null=True,
                        verbose_name="Amsterdam Schema Dataproduct verwijzing (url)",
                    ),
                ),
                (
                    "version",
                    models.CharField(
                        help_text="Het versienummer van het Data Product zoals bijgehouden door het Datateam",
                        max_length=4,
                        verbose_name="Versie",
                    ),
                ),
                (
                    "datateam",
                    models.ForeignKey(
                        help_text="Het Datateam verantwoordelijk voor en gekoppeld aan het Data Product",
                        on_delete=django.db.models.deletion.CASCADE,
                        to="beheeromgeving.datateam",
                    ),
                ),
                (
                    "distribution",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="beheeromgeving.distribution",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="APIDistribution",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "api_type",
                    models.CharField(
                        help_text="Soort API: REST, atom, etc.",
                        max_length=10,
                        verbose_name="API Type",
                    ),
                ),
                ("url", models.URLField(verbose_name="API Link (Intern)")),
                (
                    "distribution",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="apis",
                        to="beheeromgeving.distribution",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="FileDistribution",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "file_format",
                    models.CharField(
                        help_text="Het bestandsformaat: CSV, CAD, etc.",
                        max_length=10,
                        verbose_name="Bestandstype",
                    ),
                ),
                (
                    "link",
                    models.TextField(
                        help_text="Link naar het bestand dat opgeslagen is binnen de omgeving van het Datateam op het Dataplatform",
                        verbose_name="Bestand Link (Intern)",
                    ),
                ),
                (
                    "distribution",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="files",
                        to="beheeromgeving.distribution",
                    ),
                ),
            ],
        ),
    ]
