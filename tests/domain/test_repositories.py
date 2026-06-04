from datetime import UTC, datetime

import pytest

from beheeromgeving.models import Product as ORMProduct
from beheeromgeving.models import ProductWorkingCopy
from beheeromgeving.models import Team as ORMTeam
from domain.exceptions import AuthException, ObjectDoesNotExist
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

    def test_get_includes_product_count(self, orm_team, orm_product, orm_draft_product):
        repo = TeamRepository()
        team = repo.get(orm_team.id)
        assert team.product_count == 1

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

    def test_get_for_publication_status_internal_product(self, many_orm_information_products):
        repo = ProductRepository()
        orm_internal_product = many_orm_information_products[0]
        product = repo.get_for_publication_status(
            orm_internal_product.id,
            [enums.PublicationStatus.INTERNALLY_PUBLISHED],
        )
        assert isinstance(product, Product)
        assert product.id == orm_internal_product.pk

    def test_get_for_publication_status_by_name_internal_product(
        self, many_orm_information_products: list[ORMProduct]
    ):
        repo = ProductRepository()
        orm_internal_product = many_orm_information_products[0]
        product = repo.get_for_publication_status_by_name(
            orm_internal_product.name,
            [enums.PublicationStatus.INTERNALLY_PUBLISHED],
        )
        assert isinstance(product, Product)
        assert product.id == orm_internal_product.pk

    def test_get_for_publication_status_filters_contracts(self, orm_product):
        repo = ProductRepository()
        # Add an internally-published contract and ensure draft stays hidden.
        orm_product.contracts.create(
            name="internal contract",
            publication_status="I",
            publication_date=datetime(2024, 1, 1, tzinfo=UTC),
        )

        product = repo.get_for_publication_status(
            orm_product.id,
            [enums.PublicationStatus.PUBLISHED, enums.PublicationStatus.INTERNALLY_PUBLISHED],
        )
        assert product.publication_status == "P"
        assert {c.publication_status for c in product.contracts} == {"P", "I"}

    def test_get_for_publication_status_raises_when_product_status_not_allowed(
        self, many_orm_information_products
    ):
        repo = ProductRepository()
        orm_internal_product = many_orm_information_products[0]
        with pytest.raises(AuthException):
            repo.get_for_publication_status(
                orm_internal_product.id,
                [enums.PublicationStatus.PUBLISHED],
            )

    def test_get_for_publication_status_raises_when_product_does_not_exist(self):
        repo = ProductRepository()
        with pytest.raises(ObjectDoesNotExist):
            repo.get_for_publication_status(
                1337,
                [enums.PublicationStatus.PUBLISHED],
            )

    def test_get_for_publication_status_by_name_filters_contracts(self, orm_product):
        repo = ProductRepository()
        orm_product.contracts.create(
            name="internal contract",
            publication_status="I",
            publication_date=datetime(2024, 1, 1, tzinfo=UTC),
        )

        product = repo.get_for_publication_status_by_name(
            orm_product.name,
            [enums.PublicationStatus.PUBLISHED, enums.PublicationStatus.INTERNALLY_PUBLISHED],
        )
        assert product.id == orm_product.id
        assert {c.publication_status for c in product.contracts} == {"P", "I"}

    def test_get_for_publication_status_by_name_raises_when_product_status_not_allowed(
        self, many_orm_information_products
    ):
        repo = ProductRepository()
        orm_internal_product = many_orm_information_products[0]
        with pytest.raises(AuthException):
            repo.get_for_publication_status_by_name(
                orm_internal_product.name,
                [enums.PublicationStatus.PUBLISHED],
            )

    def test_list(self, orm_product):
        repo = ProductRepository()
        result = repo.list_for_publication_status([enums.PublicationStatus.PUBLISHED])

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

    def test_product_working_copy_from_domain_requires_persisted_product_id(self, orm_team):
        with pytest.raises(ValueError, match="requires a persisted product id"):
            ProductWorkingCopy.from_domain(Product(team_id=orm_team.id))

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
        distributions = list(contract.distributions.all().order_by("type"))
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
        products = repo.list_for_publication_status(
            [enums.PublicationStatus.PUBLISHED],
            order=order,
        )
        assert products[0].get(order[0]) == expect_value

    def test_order_products_list_by_created_at(self, many_orm_products: list[ORMProduct]):
        repo = ProductRepository()
        products = repo.list_for_publication_status(
            [enums.PublicationStatus.PUBLISHED],
            order=("created_at", False),
        )
        assert products[0]["last_updated"] == datetime(2025, 12, 25, 0, 34, tzinfo=UTC)

    def test_order_products_list_by_created_at_reversed(self, many_orm_products: list[ORMProduct]):
        repo = ProductRepository()
        products = repo.list_for_publication_status(
            [enums.PublicationStatus.PUBLISHED],
            order=("created_at", True),
        )
        assert products[0]["last_updated"] == datetime(2025, 12, 25, 0, 59, tzinfo=UTC)

    def test_default_order_products_list(self, many_orm_products):
        repo = ProductRepository()
        products = repo.list_for_publication_status([enums.PublicationStatus.PUBLISHED])
        assert products[0]["name"] == "naam a"
