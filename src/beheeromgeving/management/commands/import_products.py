import json
import re
from math import ceil
from pathlib import Path

import requests
from django.core.management import BaseCommand
from unidecode import unidecode

from api.datatransferobjects import (
    DataContractCreateOrUpdate,
    DataServiceCreateOrUpdate,
    DistributionCreateOrUpdate,
    ProductCreate,
    ProductUpdate,
    RefreshPeriod,
)
from domain.auth import AuthorizationRepository, AuthorizationService, authorize
from domain.exceptions import ObjectDoesNotExist, ValidationError
from domain.product import ProductRepository, ProductService, enums
from domain.product.objects import Product
from domain.team import TeamRepository, TeamService
from domain.team.objects import Team

MARKETPLACE_URL = "https://dmpfunc002.amsterdam.nl/marketplace"
SCHEMA_API_URL = "https://api.schemas.data.amsterdam.nl/v1/datasets"

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
        parser.add_argument(
            "--source",
            default="marketplace",
            help="source of the products, either 'marketplace', 'schema_api', or 'all'.",
            dest="source",
        )

    def purge(self):
        all_products = self.service.get_products()
        for product in all_products:
            print(f"deleting product: {product.name}")
            team = self.team_service.get_team(product.team_id)
            if product.id is not None:
                self.service.delete_product(product_id=product.id, scopes=[team.scope])

    def handle(self, *args, **options):
        if options.get("purge", False):
            self.purge()
            return
        if options.get("source") == "marketplace":
            self._import_from_market_place()
        elif options.get("source") == "schema_api":
            self._import_from_schema_api()
        elif options.get("source") == "all":
            self._import_from_market_place()
            self._import_from_schema_api()
        else:
            print("Invalid source")

    def _import_from_market_place(self):
        all_products = requests.get(MARKETPLACE_URL, timeout=10).json()["documents"]
        all_teams = self.team_service.get_teams()
        for product_summary in all_products:
            product = requests.get(f"{MARKETPLACE_URL}/{product_summary['id']}", timeout=10).json()
            print(f"Adding product {product['naam']}")
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
                            f"SKIPPING {product['naam']}: Cannot find team with "
                            f"name {product['dataTeam']}."
                        )
                        continue
            self.team_service.update_team(
                team_id=team.id,
                # This was not available in the team data we use.
                data={"contact_email": product["contactEmailAdres"]},
                scopes=[team.scope],
            )
            try:
                domain_product = self.service.get_product_by_name(product["naam"])
                new_product = self._update_product(domain_product, product)
            except ObjectDoesNotExist:
                new_product = self._create_product(
                    team,
                    product["naam"],
                    **self._get_product_kwargs(product),
                )
            except ValidationError as e:
                print(e.message)
                continue

            services = self._create_services(product, new_product, team)
            new_contract = self._create_contract(product, new_product, team)

            self._create_distributions(product, new_product, new_contract, services, team)
            try:
                self.service.update_publication_status(
                    product_id=new_product.id,
                    data={"publication_status": "P"},
                    scopes=[team.scope],
                )
            except ValidationError as e:
                # only happens when refresh_period cannot be parsed.
                print(e.message, product["ververstermijn"])
                continue

    def _import_from_schema_api(self):
        response = requests.get(SCHEMA_API_URL, timeout=10).json()
        all_datasets = response["results"]
        pages = ceil(response["count"] / 10)
        for n in range(2, pages + 1):
            response = requests.get(f"{SCHEMA_API_URL}?page={n}", timeout=10).json()
            all_datasets.extend(response["results"])
        for dataset in all_datasets:
            name = dataset.get("title")
            # title can be missing or empty string
            if not name:
                name = dataset["id"]
            try:
                product = self.service.get_product_by_name(name[:64])
            except ObjectDoesNotExist:
                # Create
                print(f"Adding product {name}")
                try:
                    team = self.team_service.get_team_by_name(dataset["publisher"]["name"])
                except ObjectDoesNotExist:
                    print(f"Team {dataset['publisher']['name']} doesn't exist")
                    continue
                crs = dataset.get("crs")
                crs_map = {
                    "EPSG:28992": enums.CoordRefSystem.RD,
                    "EPSG:4326": enums.CoordRefSystem.WGS84,
                    "EPSG:4258": enums.CoordRefSystem.ETRS89,
                    "EPSG:32735": enums.CoordRefSystem.UTM35S,
                }
                product = self._create_product(
                    team,
                    name[:64],
                    description=dataset.get("description"),
                    crs=crs_map[crs] if crs else None,
                    is_geo=dataset.get("crs") is not None,
                    schema_url=f"{SCHEMA_API_URL}/{to_snake_case(dataset['id'])}",
                    type=enums.ProductType.DATAPRODUCT,
                    owner=dataset["owner"][:64] if dataset.get("owner") else None,
                )
                if not product.id:
                    raise ObjectDoesNotExist from None
                auth = dataset.get("auth", [{"id": "OPENBAAR", "name": "Openbaar"}])[0]
                contract = DataContractCreateOrUpdate(
                    name=f"{name} {auth.get('name')}"[:64],
                    description=product.description,
                    scope=f"scope_{auth.get('id').lower()}",
                    confidentiality=enums.ConfidentialityLevel.OPENBAAR
                    if auth.get("id") == "OPENBAAR"
                    else None,
                )
                contract = self.service.create_contract(
                    product_id=product.id, data=contract.model_dump(), scopes=[team.scope]
                )
                path = to_snake_case(dataset["id"]).replace("_", "/")
                s = DataServiceCreateOrUpdate(
                    type=enums.DataServiceType.REST,
                    endpoint_url=f"https://api.data.amsterdam.nl/v1/{path}",
                )
                service = self.service.create_service(
                    product_id=product.id, data=s.model_dump(), scopes=[team.scope]
                )
                d = DistributionCreateOrUpdate(
                    access_service_id=service.id, type=enums.DistributionType.API
                )
                self.service.create_distribution(
                    product_id=product.id,
                    contract_id=contract.id,
                    data=d.model_dump(),
                    scopes=[team.scope],
                )

    def _get_refresh_period(self, product):
        refresh_parts = product["ververstermijn"].split(" ")
        try:
            refresh_period = RefreshPeriod(
                frequency=FREQUENCY_MAP[refresh_parts[0]], unit=UNIT_MAP[refresh_parts[-1]]
            )
        except KeyError:
            refresh_period = None
        return refresh_period

    def _get_product_kwargs(self, product):
        return {
            "description": product["beschrijving"],
            "language": enums.Language[product["taal"].upper()],
            "is_geo": product["geoData"] == "Ja",
            "crs": (
                product["geoCoördinaatreferentiesysteem"]
                if product["geoCoördinaatreferentiesysteem"] not in ["Niet van toepassing", ""]
                else None
            ),
            "schema_url": (
                "https://api.schemas.data.amsterdam.nl/v1/datasets/"
                f"{product['amsterdamSchemaDatasetVerwijzing']['datasetName']}"
                if product.get("amsterdamSchemaDatasetVerwijzing")
                else ""
            ),
            "type": enums.ProductType.DATAPRODUCT,
            "themes": [
                enums.Theme[unidecode("_".join(theme.upper().split(" ")))]
                for theme in product["themaNamen"]
            ],
            "refresh_period": self._get_refresh_period(product),
            "owner": (
                product["eigenaar"]
                if product["eigenaar"] != "Product Owner van het Datateam"
                else None
            ),
            "data_steward": product["businessDataSteward"],
        }

    def _create_product(self, team: Team, name: str, **kwargs):
        if not team.id:
            raise RuntimeError(f"Team {team.name} is missing id")
        product_dto = ProductCreate(team_id=team.id, name=name, **kwargs)
        return self.service.create_product(data=product_dto.model_dump(), scopes=[team.scope])

    def _update_product(self, domain_product: Product, product: dict):
        update_dto = ProductUpdate(
            name=domain_product.name,
            team_id=domain_product.team_id,
            **self._get_product_kwargs(product),
        )
        if not domain_product.id:
            raise ObjectDoesNotExist
        return self.service.update_product(
            product_id=domain_product.id, data=update_dto.model_dump()
        )

    def _create_services(self, product, new_product, team):
        services = []
        for service in product["api"]:
            s = DataServiceCreateOrUpdate(
                type=enums.DataServiceType[service["type"].split(" ")[0].upper()],
                endpoint_url=service["link"],
            )
            services.append(
                self.service.create_service(
                    product_id=new_product.id, data=s.model_dump(), scopes=[team.scope]
                )
            )
        return services

    def _create_contract(self, product_dict, created_product, team):
        try:
            retainment_period = int(product_dict["bewaartermijn"])
        except ValueError:
            retainment_period = None
        conf_level_map = {
            "Open": enums.ConfidentialityLevel.OPENBAAR,
            "Intern": enums.ConfidentialityLevel.INTERN,
            "Vertrouwelijk": enums.ConfidentialityLevel.VERTROUWELIJK,
        }
        PRIVACY_LEVELS = {
            "niet persoonlijk identificeerbaar": "NIET_PERSOONLIJK_IDENTIFICEERBAAR",
            "persoonlijk identificeerbaar": "PERSOONLIJK_IDENTIFICEERBAAR",
            "bijzonder identificeerbaar": "BIJZONDER_IDENTIFICEERBAAR",
        }
        c = DataContractCreateOrUpdate(
            purpose=product_dict["doelbinding"],
            name=f"{product_dict['naam']} {product_dict['vertrouwelijkheidsniveau']}"[:64],
            description=product_dict["beschrijving"],
            privacy_level=enums.PrivacyLevel[
                PRIVACY_LEVELS[product_dict["privacyniveau"].lower()]
            ],
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

    def _create_distributions(self, product: dict, new_product, new_contract, services, team):
        distributions = []
        for distribution in product["distributietype"]:
            if distribution == "API":
                for service in services:
                    d = DistributionCreateOrUpdate(
                        access_service_id=service.id, type=enums.DistributionType.API
                    )
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
                    d = DistributionCreateOrUpdate(
                        download_url=file["bestandLink"],
                        format=file["bestandstype"][:10],
                        type=enums.DistributionType.FILE,
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


def to_snake_case(name: str):
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
