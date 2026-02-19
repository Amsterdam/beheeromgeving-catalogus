import json

import pytest
from django.core.management import call_command

from beheeromgeving.management.commands.import_products import MARKETPLACE_URL, SCHEMA_API_URL
from beheeromgeving.management.commands.import_products import Command as ImportProductsCommand
from beheeromgeving.models import DataContract, DataService, Distribution, Product
from domain.product import enums


@pytest.mark.django_db
class TestImportProducts:
    def test_import_products_methods(self, product_json: dict, orm_team):
        import_products = ImportProductsCommand()

        new_product = import_products._create_product(
            orm_team, product_json["naam"], **import_products._get_product_kwargs(product_json)
        )
        assert new_product.name == product_json["naam"]

        services = import_products._create_services(product_json, new_product, orm_team)
        assert len(services) == len(product_json["api"])

        new_contract = import_products._create_contract(product_json, new_product, orm_team)
        assert new_contract.purpose == product_json["doelbinding"]

        distributions = import_products._create_distributions(
            product_json, new_product, new_contract, services, orm_team
        )
        assert len(distributions) == 4  # 3 api endpoints and 1 file

        assert Product.objects.filter(id=new_product.id).exists()

    def test_import_products(
        self,
        requests_mock,
        marketplace_json,
        marketplace_detail_json,
        schema_api_json,
        orm_team,
        orm_other_team,
    ):
        requests_mock.get(MARKETPLACE_URL, text=json.dumps(marketplace_json))
        requests_mock.get(
            f"{MARKETPLACE_URL}/bomen_stamgegevens_v1", text=json.dumps(marketplace_detail_json)
        )
        requests_mock.get(SCHEMA_API_URL, text=json.dumps(schema_api_json))
        call_command("import_products", source="all")
        assert Product.objects.count() == 2
        assert (
            Product.objects.filter(publication_status=enums.PublicationStatus.PUBLISHED).count()
            == 1
        )
        assert (
            Product.objects.filter(publication_status=enums.PublicationStatus.DRAFT).count() == 1
        )
        assert DataContract.objects.count() == 2
        assert (
            DataContract.objects.filter(publication_status=enums.PublicationStatus.DRAFT).count()
            == 1
        )
        assert (
            DataContract.objects.filter(
                publication_status=enums.PublicationStatus.PUBLISHED
            ).count()
            == 1
        )
        assert DataService.objects.count() == 4
        assert Distribution.objects.count() == 4

    def test_import_products_is_idempotent(
        self,
        requests_mock,
        marketplace_json,
        marketplace_detail_json,
        schema_api_json,
        orm_team,
        orm_other_team,
    ):
        requests_mock.get(MARKETPLACE_URL, text=json.dumps(marketplace_json))
        requests_mock.get(
            f"{MARKETPLACE_URL}/bomen_stamgegevens_v1", text=json.dumps(marketplace_detail_json)
        )
        requests_mock.get(SCHEMA_API_URL, text=json.dumps(schema_api_json))
        call_command("import_products", source="all")
        call_command("import_products", source="all")
        assert Product.objects.count() == 2
        assert (
            Product.objects.filter(publication_status=enums.PublicationStatus.PUBLISHED).count()
            == 1
        )
        assert (
            Product.objects.filter(publication_status=enums.PublicationStatus.DRAFT).count() == 1
        )
        assert DataContract.objects.count() == 2
        assert (
            DataContract.objects.filter(publication_status=enums.PublicationStatus.DRAFT).count()
            == 1
        )
        assert (
            DataContract.objects.filter(
                publication_status=enums.PublicationStatus.PUBLISHED
            ).count()
            == 1
        )
        assert DataService.objects.count() == 4
        assert Distribution.objects.count() == 4

    def test_import_products_updates_from_marketplace(
        self,
        requests_mock,
        marketplace_json,
        marketplace_detail_json,
        orm_other_team,
    ):
        requests_mock.get(MARKETPLACE_URL, text=json.dumps(marketplace_json))
        requests_mock.get(
            f"{MARKETPLACE_URL}/bomen_stamgegevens_v1", text=json.dumps(marketplace_detail_json)
        )
        call_command("import_products")

        marketplace_detail_json["beschrijving"] = "Nieuwe beschrijving"
        marketplace_detail_json["amsterdamSchemaDatasetVerwijzing"]["scope"] = "FP/MDW"
        requests_mock.get(
            f"{MARKETPLACE_URL}/bomen_stamgegevens_v1", text=json.dumps(marketplace_detail_json)
        )
        call_command("import_products")
        assert Product.objects.count() == 1
        updated_product = Product.objects.filter(name="Bomen stamgegevens").first()
        assert updated_product
        assert updated_product.description == "Nieuwe beschrijving"
        assert updated_product.contracts.count() == 1
        updated_contract = updated_product.contracts.first()
        assert updated_contract
        assert updated_contract.scopes == ["fp/mdw"]

    def test_import_products_does_not_update_from_schema_api(
        self, requests_mock, schema_api_json, orm_team
    ):
        requests_mock.get(SCHEMA_API_URL, text=json.dumps(schema_api_json))
        call_command("import_products", source="schema_api")

        schema_api_json["results"][0]["description"] = "Nieuwe beschrijving"
        requests_mock.get(SCHEMA_API_URL, text=json.dumps(schema_api_json))
        call_command("import_products", source="schema_api")
        assert Product.objects.count() == 1
        product = Product.objects.filter(name="aardgasverbruik").first()
        assert product
        assert product.description != "Nieuwe beschrijving"

    def test_import_products_purge(
        self,
        requests_mock,
        marketplace_json,
        marketplace_detail_json,
        schema_api_json,
        orm_team,
        orm_other_team,
    ):
        requests_mock.get(MARKETPLACE_URL, text=json.dumps(marketplace_json))
        requests_mock.get(
            f"{MARKETPLACE_URL}/bomen_stamgegevens_v1", text=json.dumps(marketplace_detail_json)
        )
        requests_mock.get(SCHEMA_API_URL, text=json.dumps(schema_api_json))
        call_command("import_products", source="all")
        assert Product.objects.count() == 2

        call_command("import_products", purge=True)
        assert Product.objects.count() == 0
        assert DataContract.objects.count() == 0
        assert DataService.objects.count() == 0
        assert Distribution.objects.count() == 0
