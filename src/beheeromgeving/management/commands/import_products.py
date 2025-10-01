import json
from pathlib import Path

import requests
from django.core.management import BaseCommand
from unidecode import unidecode

from api.datatransferobjects import (
    DataContract,
    DataService,
    Distribution,
    ProductDetail,
    RefreshPeriod,
)
from domain.auth import AuthorizationRepository, AuthorizationService, authorize
from domain.exceptions import ValidationError
from domain.product import ProductRepository, ProductService, enums
from domain.team import TeamRepository, TeamService

MARKETPLACE_URL = "https://dmpfunc002.amsterdam.nl/marketplace"
FREQUENCY_MAP = {
    "Een": 1,
    "Twee": 2,
    "Drie": 3,
    "Vier": 4,
    "Dagelijks": 1,
    "Maandelijks": 1,
    "Wekelijks": 1,
    "Jaarlijks": 1,
}
UNIT_MAP = {
    "maand": enums.TimeUnit.MONTH,
    "dag": enums.TimeUnit.DAY,
    "uur": enums.TimeUnit.HOUR,
    "jaar": enums.TimeUnit.YEAR,
    "week": enums.TimeUnit.WEEK,
    "Dagelijks": enums.TimeUnit.DAY,
    "Wekelijks": enums.TimeUnit.WEEK,
    "Maandelijks": enums.TimeUnit.MONTH,
    "Jaarlijks": enums.TimeUnit.YEAR,
}


class Command(BaseCommand):
    service: ProductService
    team_service: TeamService

    def __init__(self):
        authorize.set_auth_service(AuthorizationService(AuthorizationRepository()))
        self.service = ProductService(ProductRepository())
        self.team_service = TeamService(TeamRepository())

    def add_arguments(self, parser):
        parser.add_argument(
            "--purge",
            default=False,
            help="Remove products",
            dest="purge",
            action="store_true",
        )

    def purge(self):
        all_products = self.service.get_products()
        for product in all_products:
            print(f"deleting product: {product.name}")
            team = self.team_service.get_team(product.team_id)
            self.service.delete_product(product_id=product.id, scopes=[team.scope])

    def handle(self, *args, **options):
        if options.get("purge", False):
            self.purge()
            return
        all_products = requests.get(MARKETPLACE_URL, timeout=10).json()["documents"]
        all_teams = self.team_service.get_teams()
        for product_summary in all_products:
            product = requests.get(f"{MARKETPLACE_URL}/{product_summary["id"]}", timeout=10).json()
            print(f"Adding product {product["naam"]}")
            team = None
            try:
                team = next(team for team in all_teams if team.name == product["dataTeam"])
            except StopIteration:
                with open(Path(__file__).parent / "teammap.json") as team_file:
                    team_map = json.load(team_file)
                    try:
                        team = next(
                            team
                            for team in all_teams
                            if team.acronym == team_map[product["dataTeam"]]
                        )
                    except StopIteration:
                        print(
                            f"SKIPPING {product["naam"]}: Cannot find team with "
                            f"name {product["dataTeam"]}."
                        )
                        continue
            self.team_service.update_team(
                team_id=team.id,
                # This was not available in the team data we use.
                data={"contact_email": product["contactEmailAdres"]},
                scopes=[team.scope],
            )
            try:
                new_product = self.create_product(product, team)
            except ValidationError as e:
                print(e.message)
                continue

            services = self.create_services(product, new_product, team)
            new_contract = self.create_contract(product, new_product, team)

            self.create_distributions(product, new_product, new_contract, services, team)

    def create_product(self, product, team):
        refresh_parts = product["ververstermijn"].split(" ")
        try:
            refresh_period = RefreshPeriod(
                frequency=FREQUENCY_MAP[refresh_parts[0]], unit=UNIT_MAP[refresh_parts[-1]]
            )
        except KeyError:
            refresh_period = None
        p = ProductDetail(
            team_id=team.id,
            name=product["naam"],
            description=product["beschrijving"],
            language=enums.Language[product["taal"].upper()],
            is_geo=product["geoData"] == "Ja",
            crs=(
                product["geoCoördinaatreferentiesysteem"]
                if product["geoCoördinaatreferentiesysteem"] not in ["Niet van toepassing", ""]
                else None
            ),
            schema_url=(
                "https://schemas.data.amsterdam.nl/datasets"
                f"{product["amsterdamSchemaVerwijzing"]["datasetName"]}/dataset"
                if product.get("amsterdamSchemaVerwijzing")
                else ""
            ),
            type=enums.ProductType.DATAPRODUCT,
            themes=[
                enums.Theme[unidecode("_".join(theme.upper().split(" ")))]
                for theme in product["themaNamen"]
            ],
            has_personal_data=product["vertrouwelijkheidsniveau"] != "Open",
            has_special_personal_data=product["vertrouwelijkheidsniveau"] != "Open"
            and product["privacyniveau"] != "Niet persoonlijk identificeerbaar",
            publication_status=enums.PublicationStatus.PUBLISHED,
            refresh_period=refresh_period,
            owner=(
                product["eigenaar"]
                if product["eigenaar"] != "Product Owner van het Datateam"
                else None
            ),
            data_steward=product["businessDataSteward"],
        )
        return self.service.create_product(data=p.model_dump(), scopes=[team.scope])

    def create_services(self, product, new_product, team):
        services = []
        for service in product["api"]:
            s = DataService(
                type=enums.DataServiceType[service["type"].split(" ")[0].upper()],
                endpoint_url=service["link"],
            )
            services.append(
                self.service.create_service(
                    product_id=new_product.id, data=s.model_dump(), scopes=[team.scope]
                )
            )
        return services

    def create_contract(self, product_dict, created_product, team):
        try:
            retainment_period = int(product_dict["bewaartermijn"])
        except ValueError:
            retainment_period = None
        conf_level_map = {
            "Open": enums.ConfidentialityLevel.OPENBAAR,
            "Intern": enums.ConfidentialityLevel.INTERN,
            "Vertrouwelijk": enums.ConfidentialityLevel.VERTROUWELIJK,
        }
        c = DataContract(
            publication_status=enums.PublicationStatus.PUBLISHED,
            purpose=product_dict["doelbinding"],
            name=f"{product_dict["naam"]} {product_dict["vertrouwelijkheidsniveau"]}"[:64],
            description=product_dict["beschrijving"],
            has_personal_data=created_product.has_personal_data,
            has_special_personal_data=created_product.has_special_personal_data,
            scope=(
                product_dict["amsterdamSchemaVerwijzing"]["scope"]
                if product_dict.get("amsterdamSchemaVerwijzing")
                else "scope_openbaar"
            ),
            confidentiality=conf_level_map[product_dict["vertrouwelijkheidsniveau"]],
            start_date=product_dict["startDatumContract"],
            retainment_period=retainment_period,
        )
        return self.service.create_contract(
            product_id=created_product.id, data=c.model_dump(), scopes=[team.scope]
        )

    def create_distributions(self, product: dict, new_product, new_contract, services, team):
        distributions = []
        for distribution in product["distributietype"]:
            if distribution == "API":
                for service in services:
                    d = Distribution(access_service_id=service.id, type=enums.DistributionType.API)
                    distributions.append(
                        self.service.create_distribution(
                            product_id=new_product.id,
                            contract_id=new_contract.id,
                            data=d.model_dump(),
                            scopes=[team.scope],
                        )
                    )
            elif distribution == "Bestand":
                for file in product["bestanden"]:
                    d = Distribution(
                        download_url=file["bestandLink"],
                        format=file["bestandstype"][:10],
                        refresh_period=new_product.refresh_period,
                    )
                    distributions.append(
                        self.service.create_distribution(
                            product_id=new_product.id,
                            contract_id=new_contract.id,
                            data=d.model_dump(),
                            scopes=[team.scope],
                        )
                    )
        return distributions
