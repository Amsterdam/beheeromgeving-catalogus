import pytest
from django.apps import apps
from importlib import import_module

from beheeromgeving.migration_utils import (
    SEPARATORS,
    fix_distribution_format,
    revert_team_scopes,
    set_po_name,
    update_team_scopes,
)
from beheeromgeving.models import Distribution, ProductPublishedSnapshot


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

    def test_migration_0021_snapshot_backfill(self, orm_product):
        module = import_module("beheeromgeving.migrations.0021_backfill_productpublishedsnapshot")
        ProductPublishedSnapshot.objects.filter(product_id=orm_product.id).delete()
        module.backfill_published_snapshots(apps, None)
        record = ProductPublishedSnapshot.objects.get(product_id=orm_product.id)
        assert record.snapshot["id"] == orm_product.id
        assert record.snapshot["_snapshot_version"] == 1
