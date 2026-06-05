from datetime import UTC, datetime

import pytest

from beheeromgeving.models import DataContractRevision, ProductRevision
from beheeromgeving.models import Product as ORMProduct
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

    def test_product_revision_from_domain_requires_persisted_product_id(self, orm_team):
        with pytest.raises(ValueError, match="requires a persisted product id"):
            ProductRevision.from_domain(Product(team_id=orm_team.id))

    def test_contract_revision_from_domain_requires_persisted_contract_id(self, orm_product):
        with pytest.raises(ValueError, match="requires a persisted contract id"):
            DataContractRevision.from_domain(DataContract(), orm_product.id)

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

    def test_save_contract_revision_and_get_contract_revision_with_schema_url(
        self, orm_incomplete_product: ORMProduct
    ):
        repo = ProductRepository()
        product = repo.get(orm_incomplete_product.pk)
        contract = product.contracts[0]
        assert contract.id

        contract.name = "beheer bomen draft"
        saved_contract = repo.save_contract_revision(
            product_id=orm_incomplete_product.pk,
            contract=contract,
        )
        fetched_contract = repo.get_contract_revision(
            product_id=orm_incomplete_product.pk,
            contract_id=contract.id,
        )

        assert saved_contract.name == "beheer bomen draft"
        assert fetched_contract.name == "beheer bomen draft"
        assert fetched_contract.schema_url == (
            "https://schemas.data.amsterdam.nl/datasets/bomen/dataset?"
            "scopes=bomen_beheer&tables=stamgegevens,takgegevens"
        )

    def test_save_contract_revision_updates_existing_revision(self, orm_draft_product: ORMProduct):
        repo = ProductRepository()
        product = repo.get(orm_draft_product.pk)
        contract = product.contracts[0]
        assert contract.id

        contract.name = "eerste draft naam"
        repo.save_contract_revision(product_id=orm_draft_product.pk, contract=contract)

        contract.purpose = "bijgewerkt doel"
        updated_contract = repo.save_contract_revision(
            product_id=orm_draft_product.pk,
            contract=contract,
        )

        assert DataContractRevision.objects.filter(contract_id=contract.id).count() == 1
        assert updated_contract.name == "eerste draft naam"
        assert updated_contract.purpose == "bijgewerkt doel"
        assert updated_contract.schema_url == (
            "https://schemas.data.amsterdam.nl/datasets/bomen/dataset?scopes=bomen_beheer"
        )

    def test_save_contract_revision_round_trips_live_and_draft_distribution_ids(
        self, orm_product: ORMProduct
    ):
        repo = ProductRepository()
        product = repo.get(orm_product.pk)
        contract = product.contracts[0]
        assert contract.id is not None

        live_contract = orm_product.contracts.first()
        assert live_contract is not None
        live_distributions = list(
            live_contract.distributions.order_by("id").values(
                "id",
                "access_service_id",
            )
        )

        contract.distributions = [
            Distribution(
                id=live_distributions[0]["id"],
                access_service_id=live_distributions[0]["access_service_id"],
                type=enums.DistributionType.API,
            ),
            Distribution(
                id=live_distributions[1]["id"],
                download_url="https://bomen.amsterdam.nl/beheer-updated.csv",
                format="csv",
                type=enums.DistributionType.FILE,
            ),
            Distribution(
                download_url="https://bomen.amsterdam.nl/draft.geojson",
                format="geojson",
                type=enums.DistributionType.FILE,
            ),
        ]

        saved_contract = repo.save_contract_revision(product_id=orm_product.pk, contract=contract)
        fetched_contract = repo.get_contract_revision(
            product_id=orm_product.pk,
            contract_id=contract.id,
        )

        live_distribution_ids = {distribution["id"] for distribution in live_distributions}
        saved_ids = {distribution.id for distribution in saved_contract.distributions}
        fetched_ids = {distribution.id for distribution in fetched_contract.distributions}
        draft_distribution = next(
            distribution
            for distribution in fetched_contract.distributions
            if distribution.download_url == "https://bomen.amsterdam.nl/draft.geojson"
        )

        assert live_distribution_ids.issubset(saved_ids)
        assert live_distribution_ids.issubset(fetched_ids)
        assert draft_distribution.id is not None
        assert draft_distribution.id < 0
        assert (
            next(
                distribution
                for distribution in fetched_contract.distributions
                if distribution.id == draft_distribution.id
            ).download_url
            == "https://bomen.amsterdam.nl/draft.geojson"
        )

        orm_product.refresh_from_db()
        live_contract = orm_product.contracts.first()
        assert live_contract is not None
        assert live_contract.distributions.count() == 2
        assert not live_contract.distributions.filter(
            download_url="https://bomen.amsterdam.nl/draft.geojson"
        ).exists()

    def test_publish_contract_revision_assigns_live_ids_and_removes_revision(
        self, orm_product: ORMProduct
    ):
        repo = ProductRepository()
        product = repo.get(orm_product.pk)
        contract = product.contracts[0]
        assert contract.id is not None

        live_contract = orm_product.contracts.first()
        assert live_contract is not None
        live_distributions = list(
            live_contract.distributions.order_by("id").values(
                "id",
                "access_service_id",
            )
        )

        contract.name = "gepubliceerde draft naam"
        contract.distributions = [
            Distribution(
                id=live_distributions[0]["id"],
                access_service_id=live_distributions[0]["access_service_id"],
                type=enums.DistributionType.API,
            ),
            Distribution(
                id=live_distributions[1]["id"],
                download_url="https://bomen.amsterdam.nl/beheer-updated.csv",
                format="csv",
                type=enums.DistributionType.FILE,
            ),
            Distribution(
                download_url="https://bomen.amsterdam.nl/published.geojson",
                format="geojson",
                type=enums.DistributionType.FILE,
            ),
        ]

        repo.save_contract_revision(product_id=orm_product.pk, contract=contract)

        published_contract = repo.publish_contract_revision(
            product_id=orm_product.pk,
            contract_id=contract.id,
        )

        published_distribution = next(
            distribution
            for distribution in published_contract.distributions
            if distribution.download_url == "https://bomen.amsterdam.nl/published.geojson"
        )

        assert published_contract.id == contract.id
        assert published_contract.name == "gepubliceerde draft naam"
        assert published_distribution.id is not None
        assert published_distribution.id > 0
        assert published_distribution.id not in {d["id"] for d in live_distributions}
        assert not DataContractRevision.objects.filter(contract_id=contract.id).exists()

        orm_product.refresh_from_db()
        live_contract = orm_product.contracts.get(pk=contract.id)
        assert live_contract.name == "gepubliceerde draft naam"
        assert live_contract.distributions.count() == 3
        assert live_contract.distributions.filter(
            download_url="https://bomen.amsterdam.nl/published.geojson"
        ).exists()

    def test_delete_contract_revision(self, orm_product: ORMProduct):
        repo = ProductRepository()
        product = repo.get(orm_product.pk)
        contract = product.contracts[0]
        assert contract.id

        repo.save_contract_revision(product_id=orm_product.pk, contract=contract)

        deleted_id = repo.delete_contract_revision(
            product_id=orm_product.pk,
            contract_id=contract.id,
        )

        assert deleted_id == contract.id
        assert not DataContractRevision.objects.filter(contract_id=contract.id).exists()

    def test_get_contract_revision_non_existent(self, orm_product: ORMProduct):
        repo = ProductRepository()

        with pytest.raises(ObjectDoesNotExist, match="Contract revision"):
            repo.get_contract_revision(product_id=orm_product.pk, contract_id=1337)

    def test_save_contract_revision_non_existent_live_contract(self, orm_product: ORMProduct):
        repo = ProductRepository()
        contract = DataContract(id=1337, name="missing contract")

        with pytest.raises(ObjectDoesNotExist):
            repo.save_contract_revision(product_id=orm_product.pk, contract=contract)

    def test_delete_contract_revision_non_existent(self, orm_product: ORMProduct):
        repo = ProductRepository()

        with pytest.raises(ObjectDoesNotExist, match="Contract revision"):
            repo.delete_contract_revision(product_id=orm_product.pk, contract_id=1337)

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
