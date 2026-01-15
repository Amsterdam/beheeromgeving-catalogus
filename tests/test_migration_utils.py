import pytest
from django.apps import apps

from beheeromgeving.migration_utils import (
    SEPARATORS,
    fix_distribution_format,
    revert_team_scopes,
    update_team_scopes,
)
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

    def test_migration_0012(self, orm_team, orm_other_team):
        update_team_scopes(apps, None)
        for team in [orm_team, orm_other_team]:
            team.refresh_from_db()
            assert team.scope == f"publisher.{team.acronym}"

    def test_migration_0012_revert(self, orm_team, orm_other_team):
        revert_team_scopes(apps, None)
        for team in [orm_team, orm_other_team]:
            team.refresh_from_db()
            assert team.scope == f"publisher-p-{team.acronym.lower()}"
