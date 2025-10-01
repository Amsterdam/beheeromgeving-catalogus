import pytest

from beheeromgeving.management.commands.import_products import Command as ImportProductsCommand
from beheeromgeving.models import Product


@pytest.mark.django_db
class TestImportProducts:
    def test_import_products(self, product_json: dict, orm_team):
        import_products = ImportProductsCommand()

        new_product = import_products.create_product(product_json, orm_team)
        assert new_product.name == product_json["naam"]

        services = import_products.create_services(product_json, new_product, orm_team)
        assert len(services) == len(product_json["api"])

        new_contract = import_products.create_contract(product_json, new_product, orm_team)
        assert new_contract.purpose == product_json["doelbinding"]

        distributions = import_products.create_distributions(
            product_json, new_product, new_contract, services, orm_team
        )
        assert len(distributions) == 4  # 3 api endpoints and 1 file

        assert Product.objects.filter(id=new_product.id).exists()
