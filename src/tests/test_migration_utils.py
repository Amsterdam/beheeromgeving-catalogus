import pytest
from django.apps import apps

from beheeromgeving.migration_utils import SEPARATORS, fix_distribution_format
from beheeromgeving.models import Distribution


@pytest.mark.django_db
class TestMigrationUtils:
    @pytest.fixture()
    def orm_distributions(self, orm_product):
        contract = orm_product.contracts.first()
        distributions = []
        for sep in SEPARATORS:
            distributions.append(
                Distribution.objects.create(contract=contract, format=f"CSV{sep}EXTRA", type="F")
            )
        return distributions

    def test_migration_0010(self, orm_distributions):
        fix_distribution_format(apps, None)
        for distribution in orm_distributions:
            distribution.refresh_from_db()
            assert distribution.format == "CSV"
