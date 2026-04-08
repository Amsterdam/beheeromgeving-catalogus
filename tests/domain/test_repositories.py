from datetime import UTC, datetime

import pytest

from beheeromgeving.models import Product as ORMProduct
from beheeromgeving.models import ProductPublishedSnapshot
from beheeromgeving.models import Team as ORMTeam
from domain.exceptions import ObjectDoesNotExist
from domain.product import (
    DataContract,
    DataService,
    Distribution,
    Product,
    ProductRepository,
    RefreshPeriod,
    enums,
)
from domain.team import Team, TeamRepository


@pytest.mark.django_db
class TestTeamRepository:
    def test_get(self, orm_team):
        repo = TeamRepository()
        team = repo.get(orm_team.id)
        assert isinstance(team, Team)
        assert team.id == orm_team.id

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_get_non_existent(self, orm_team):
        repo = TeamRepository()
        repo.get(1337)

    def test_list(self, orm_team):
        repo = TeamRepository()
        result = repo.list()
        assert len(result) == 1
        assert isinstance(result[0], Team)

    def test_delete(self, orm_team):
        repo = TeamRepository()
        repo.delete(orm_team.id)

        assert not ORMTeam.objects.filter(id=orm_team.id).exists()

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_delete_non_existent(self):
        repo = TeamRepository()
        repo.delete(1337)

    def test_save(self, team):
        repo = TeamRepository()
        repo.save(team)

        assert ORMTeam.objects.filter(id=team.id).exists()

    def test_save_updates(self, orm_team):
        repo = TeamRepository()
        team = repo.get(orm_team.id)
        team.contact_email = "newmail@amsterdam.nl"
        repo.save(team)

        assert ORMTeam.objects.filter(
            id=orm_team.id, contact_email="newmail@amsterdam.nl"
        ).exists()

    def test_get_after_save(self, team):
        repo = TeamRepository()
        repo.save(team)
        saved_team = repo.get(team.id)
        assert team == saved_team

    def test_get_by_name(self, orm_team):
        repo = TeamRepository()
        result = repo.get_by_name("datadiensten")
        assert result.id == orm_team.id

    def test_get_by_name_inexistent(self, orm_team):
        repo = TeamRepository()
        with pytest.raises(ObjectDoesNotExist):
            repo.get_by_name("non_existent")


@pytest.mark.django_db
class TestProductRepository:
    def test_get(self, orm_product):
        repo = ProductRepository()
        product = repo.get(orm_product.id)

        assert isinstance(product, Product)
        assert product.id == orm_product.id

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_get_non_existent(self):
        repo = ProductRepository()
        repo.get(1337)

    def test_list(self, orm_product):
        repo = ProductRepository()
        result = repo.list()

        assert len(result) == 1
        assert result[0]["id"] == orm_product.id

    def test_delete(self, orm_product):
        repo = ProductRepository()
        repo.delete(orm_product.id)

        assert not ORMProduct.objects.filter(id=orm_product.id).exists()

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_delete_non_existent(self):
        repo = ProductRepository()
        repo.delete(1337)

    def test_save(self, product, orm_team):
        repo = ProductRepository()
        product.team_id = orm_team.id
        repo.save(product)

        assert ORMProduct.objects.filter(id=product.id).exists()

    def test_save_updates(self, orm_product, orm_team):
        repo = ProductRepository()
        product = repo.get(orm_product.id)
        product.owner = "owner@amsterdam.nl"
        repo.save(product)

        assert ORMProduct.objects.filter(id=orm_product.id, _owner="owner@amsterdam.nl").exists()

    def test_get_after_save(self, product, orm_team):
        repo = ProductRepository()
        product.team_id = orm_team.id
        repo.save(product)
        saved_product = repo.get(product.id)
        assert saved_product.team_id == orm_team.id
        assert saved_product.last_updated > product.last_updated

    def test_save_updates_services(self, orm_product: ORMProduct):
        repo = ProductRepository()
        product = repo.get(orm_product.pk)
        product.services.append(
            DataService(
                type=enums.DataServiceType.WMS,
                endpoint_url="https://api.data.amsterdam.nl/v1/wms/bomen",
            )
        )
        repo.save(product)

        orm_product.refresh_from_db()
        services = list(orm_product.services.all())
        assert services[-1].type == "WMS"
        assert services[-1].endpoint_url == "https://api.data.amsterdam.nl/v1/wms/bomen"

    def test_save_updates_contracts(self, orm_product: ORMProduct):
        repo = ProductRepository()
        product = repo.get(orm_product.pk)
        product.contracts.append(
            DataContract(publication_status=enums.PublicationStatus.DRAFT, name="Geheim Contract")
        )
        repo.save(product)

        orm_product.refresh_from_db()
        contracts = list(orm_product.contracts.all())
        assert contracts[-1].publication_status == "D"
        assert contracts[-1].name == "Geheim Contract"

    def test_save_updates_distributions(self, orm_product: ORMProduct):
        repo = ProductRepository()
        product = repo.get(orm_product.pk)
        product.contracts[0].distributions = [
            Distribution(
                id=product.contracts[0].distributions[0].id,
                type=enums.DistributionType.API,
                access_service_id=product.services[0].id,
                refresh_period=RefreshPeriod.from_dict({"frequency": 1, "unit": "HOUR"}),
            ),
            Distribution(
                type=enums.DistributionType.DASHBOARD,
                access_url="https://bomen.amsterdam.nl/dashboard",
            ),
            Distribution(
                type=enums.DistributionType.FILE,
                format="txt",
                download_url="https://bomen.amsterdam.nl/bomen.txt",
            ),
        ]
        repo.save(product)

        orm_product.refresh_from_db()
        contract = orm_product.contracts.first()
        assert hasattr(contract, "distributions")
        distributions = list(contract.distributions.all())
        assert len(distributions) == 3
        assert distributions[0].type == "A"
        assert distributions[0].access_service == orm_product.services.first()
        assert distributions[0].refresh_period == "1.HOUR"

        assert distributions[1].type == "D"
        assert distributions[1].access_url == "https://bomen.amsterdam.nl/dashboard"

        assert distributions[2].type == "F"
        assert distributions[2].format == "txt"
        assert distributions[2].download_url == "https://bomen.amsterdam.nl/bomen.txt"

    @pytest.mark.parametrize(
        "order,expect_value",
        [
            (("name", False), "naam a"),
            (("name", True), "naam z"),
            (
                ("last_updated", False),
                datetime(2025, 12, 25, 0, 34, tzinfo=UTC),
            ),
            (("last_updated", True), datetime(2025, 12, 25, 0, 59, tzinfo=UTC)),
        ],
    )
    def test_order_products_list(self, many_orm_products: list[ORMProduct], order, expect_value):
        repo = ProductRepository()
        products = repo.list(order=order)
        print(products[0])
        assert products[0].get(order[0]) == expect_value

    def test_order_products_list_by_created_at(self, many_orm_products: list[ORMProduct]):
        repo = ProductRepository()
        products = repo.list(order=("created_at", False))
        assert products[0]["last_updated"] == datetime(2025, 12, 25, 0, 34, tzinfo=UTC)

    def test_order_products_list_by_created_at_reversed(self, many_orm_products: list[ORMProduct]):
        repo = ProductRepository()
        products = repo.list(order=("created_at", True))
        assert products[0]["last_updated"] == datetime(2025, 12, 25, 0, 59, tzinfo=UTC)

    def test_default_order_products_list(self, many_orm_products):
        repo = ProductRepository()
        products = repo.list()
        assert products[0]["name"] == "naam a"

    def test_get_published_uses_snapshot_when_available(self, orm_product):
        repo = ProductRepository()
        repo.save_published_snapshot(orm_product.id)
        ProductPublishedSnapshot.objects.filter(product_id=orm_product.id).update(
            snapshot={
                "_snapshot_version": 1,
                "id": orm_product.id,
                "name": "Snapshot Name",
                "description": orm_product.description,
                "language": orm_product.language,
                "is_geo": orm_product.is_geo,
                "crs": orm_product.crs,
                "schema_url": orm_product.schema_url,
                "type": orm_product.type,
                "contracts": [],
                "themes": orm_product.themes,
                "last_updated": orm_product.last_updated.isoformat(),
                "created_at": orm_product.created_at.isoformat(),
                "refresh_period": {"frequency": 3, "unit": "MONTH"},
                "publication_status": orm_product.publication_status,
                "owner": orm_product.owner,
                "contact_email": orm_product.contact_email,
                "data_steward": orm_product.data_steward,
                "services": [],
                "sources": [],
                "sinks": [],
                "team_id": orm_product.team_id,
            }
        )
        published = repo.get_published(orm_product.id)
        assert published.name == "Snapshot Name"

    def test_get_published_by_name_uses_fallback_without_snapshot(self, orm_product):
        repo = ProductRepository()
        ProductPublishedSnapshot.objects.filter(product_id=orm_product.id).delete()
        published = repo.get_published_by_name("Bomen")
        assert published.id == orm_product.id
