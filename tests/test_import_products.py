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
        assert DataService.objects.count() == 4
        assert Distribution.objects.count() == 4
