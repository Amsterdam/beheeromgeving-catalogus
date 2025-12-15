from datetime import UTC, datetime

import pytest

from beheeromgeving.models import Product as ORMProduct
from beheeromgeving.models import Team as ORMTeam
from domain.exceptions import ObjectDoesNotExist
from domain.product import (
    DataContract,
    DataService,
    Distribution,
    Product,
    ProductRepository,
    RefreshPeriod,
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
        assert result[0].id == orm_product.id

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
        product = repo.get(orm_product.id)
        product.services.append(
            DataService(type="WMS", endpoint_url="https://api.data.amsterdam.nl/v1/wms/bomen")
        )
        repo.save(product)

        orm_product.refresh_from_db()
        services = list(orm_product.services.all())
        assert services[-1].type == "WMS"
        assert services[-1].endpoint_url == "https://api.data.amsterdam.nl/v1/wms/bomen"

    def test_save_updates_contracts(self, orm_product: ORMProduct):
        repo = ProductRepository()
        product = repo.get(orm_product.id)
        product.contracts.append(DataContract(publication_status="D", name="Geheim Contract"))
        repo.save(product)

        orm_product.refresh_from_db()
        contracts = list(orm_product.contracts.all())
        assert contracts[-1].publication_status == "D"
        assert contracts[-1].name == "Geheim Contract"

    def test_save_updates_distributions(self, orm_product: ORMProduct):
        repo = ProductRepository()
        product = repo.get(orm_product.id)
        product.contracts[0].distributions = [
            Distribution(
                id=product.contracts[0].distributions[0].id,
                type="A",
                access_service_id=product.services[0].id,
                refresh_period=RefreshPeriod.from_dict({"frequency": 1, "unit": "HOUR"}),
            ),
            Distribution(type="D", access_url="https://bomen.amsterdam.nl/dashboard"),
            Distribution(
                type="F", format="txt", download_url="https://bomen.amsterdam.nl/bomen.txt"
            ),
        ]
        repo.save(product)

        orm_product.refresh_from_db()
        contract = orm_product.contracts.first()
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
            (("created_at", False), datetime(2025, 12, 25, 0, 34, tzinfo=UTC)),
            (("created_at", True), datetime(2025, 12, 25, 0, 59, tzinfo=UTC)),
        ],
    )
    def test_order_products_list(self, many_orm_products: list[ORMProduct], order, expect_value):
        repo = ProductRepository()
        products = repo.list(order=order)
        assert getattr(products[0], order[0]) == expect_value

    def test_default_order_products_list(self, many_orm_products):
        repo = ProductRepository()
        products = repo.list()
        assert products[0].name == "naam a"
