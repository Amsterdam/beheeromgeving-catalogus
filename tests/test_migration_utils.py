import pytest
from django.apps import apps

from beheeromgeving.migration_utils import (
    SEPARATORS,
    fix_distribution_format,
    revert_team_scopes,
    set_po_name,
    set_publication_dates,
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

    def test_set_po_name(self, orm_team, orm_other_team):
        set_po_name(apps, None)
        for team in [orm_team, orm_other_team]:
            team.refresh_from_db()
            assert team.po_name == f"PO team {team.acronym}"

    def test_set_publication_dates(self, orm_product):
        # Set publication status to 'Published' without publication date
        orm_contract = orm_product.contracts.first()
        orm_contract.publication_status = "P"
        orm_contract.save()
        orm_product.publication_status = "P"
        orm_product.save()

        set_publication_dates(apps, None)

        orm_contract.refresh_from_db()
        orm_product.refresh_from_db()

        assert orm_contract.publication_date is not None
        assert orm_product.publication_date is not None
