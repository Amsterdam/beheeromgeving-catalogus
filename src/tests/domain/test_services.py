import pytest
from django.conf import settings

from domain.exceptions import NotAuthorized, ObjectDoesNotExist, ValidationError
from domain.product import DataContract, DataService, Product, ProductService
from domain.team import Team, TeamService

ADMIN_SCOPE = [settings.ADMIN_ROLE_NAME]
UNAUTHORIZED = ["unauthorized_scope"]
TEAM_BOR = ["scope_bor"]


class TestTeamService:
    def test_get_team(self, team_service: TeamService, team: Team):
        result = team_service.get_team(team.id)
        assert result == team

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_get_team_non_existent(self, team_service: TeamService):
        team_service.get_team(1337)  # non-existent id

    def test_get_teams(self, team_service: TeamService, team: Team):
        result = team_service.get_teams()
        assert result == [team]

    def test_create_team_by_admin(self, team_service: TeamService):
        team_data = {
            "name": "Beheer Openbare Ruimte",
            "acronym": "BOR",
            "description": "",
            "po_name": "Jan Bor",
            "po_email": "j.bor@amsterdam.nl",
            "contact_email": "bor@amsterdam.nl",
            "scope": "scope_bor",
        }
        result = team_service.create_team(data=team_data, scopes=ADMIN_SCOPE)

        assert result.acronym == "BOR"
        assert len(team_service.get_teams()) == 2

    @pytest.mark.parametrize(
        "scopes",
        [pytest.param(UNAUTHORIZED, id="Unauthorized"), pytest.param(TEAM_BOR, id="Team Scope")],
    )
    @pytest.mark.xfail(raises=NotAuthorized)
    def test_create_team_unauthorized(self, team_service: TeamService, scopes):
        team_data = {
            "name": "Beheer Openbare Ruimte",
            "acronym": "BOR",
            "description": "",
            "po_name": "Jan Bor",
            "po_email": "j.bor@amsterdam.nl",
            "contact_email": "bor@amsterdam.nl",
            "scope": "scope_bor",
        }
        team_service.create_team(data=team_data, scopes=scopes)

    def test_update_team(self, team_service: TeamService, team: Team):

        team_service.update_team(
            team_id=team.id, data={"description": "New Description"}, scopes=ADMIN_SCOPE
        )

        result = team_service.get_team(team.id)
        assert result.description == "New Description"

    @pytest.mark.xfail(raises=NotAuthorized)
    def test_update_team_unauthorized_field(self, team_service: TeamService, team: Team):
        team_service.update_team(
            team_id=team.id, data={"description": "New Description"}, scopes=[team.scope]
        )

    def test_update_team_by_team_member(self, team_service: TeamService, team: Team):
        team_service.update_team(
            team_id=team.id,
            data={
                "po_name": "Someone Else",
                "po_email": "s.else@amsterdam.nl",
                "contact_email": "new.email@amsterdam.nl",
            },
            scopes={team.scope},
        )

        result = team_service.get_team(team.id)
        assert result.po_name == "Someone Else"
        assert result.po_email == "s.else@amsterdam.nl"
        assert result.contact_email == "new.email@amsterdam.nl"

    @pytest.mark.xfail(raises=NotAuthorized)
    def test_update_team_by_other_team_unauthorized(
        self, team_service: TeamService, team: Team, other_team: Team
    ):
        team_service._persist(other_team)
        team_service.update_team(
            team_id=team.id,
            data={
                "po_name": "Someone Else",
                "po_email": "s.else@amsterdam.nl",
                "contact_email": "new.email@amsterdam.nl",
            },
            scopes={other_team.scope},
        )

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_update_team_non_existent(self, team_service: TeamService):
        team_service.update_team(
            team_id=1337, data={"description": "New Description"}, scopes=ADMIN_SCOPE
        )

    def test_delete_team_by_admin(self, team_service: TeamService, team: Team):
        team_service.delete_team(team_id=team.id, scopes=ADMIN_SCOPE)

        assert len(team_service.get_teams()) == 0

    @pytest.mark.xfail(raises=NotAuthorized)
    def test_delete_team_unauthorized(self, team_service: TeamService, team: Team):
        team_service.delete_team(team_id=team.id, scopes=UNAUTHORIZED)

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_delete_team_non_existent(self, team_service: TeamService):
        team_service.delete_team(team_id=1337, scopes=ADMIN_SCOPE)  # non-existent


class TestProductService:
    def test_get_products(self, product_service: ProductService, product: Product):
        result = product_service.get_products()

        assert result == [product]

    def test_get_product(self, product_service: ProductService, product: Product):
        result = product_service.get_product(product.id)

        assert result == product

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_get_product_non_existent(self, product_service: ProductService):
        product_service.get_product(1337)  # non-existent

    def test_create_product(self, product_service: ProductService, team: Team):
        data = {"type": "D", "team_id": team.id}
        result = product_service.create_product(data=data, scopes=[team.scope])

        assert len(product_service.get_products()) == 2  # service initialized with 1 product
        assert result.type == "D"

    @pytest.mark.xfail(raises=NotAuthorized)
    def test_create_product_other_team(
        self, team: Team, other_team: Team, product_service: ProductService
    ):
        data = {"type": "D", "publication_status": "D", "team_id": team.id}
        product_service.create_product(data=data, scopes=[other_team.scope])

    def test_update_product(self, product_service: ProductService, product: Product, team: Team):
        data = {"description": "a fancy product"}
        product_service.update_product(product_id=product.id, data=data, scopes=[team.scope])

        result = product_service.get_product(product.id)

        assert result.description == "a fancy product"

    @pytest.mark.xfail(raises=NotAuthorized)
    def test_update_product_non_existent(self, product_service: ProductService, team: Team):
        data = {"description": "a fancy product"}
        product_service.update_product(product_id=1337, data=data, scopes=[team.scope])

    def test_delete_product(self, product_service: ProductService, product: Product, team: Team):
        product_service.delete_product(product_id=product.id, scopes=[team.scope])

        assert len(product_service.get_products()) == 0

    @pytest.mark.xfail(raises=NotAuthorized)
    def test_delete_product_non_existent(self, product_service: ProductService, team: Team):
        product_service.delete_product(product_id=1337, scopes=[team.scope])  # non-existent

    def test_get_contracts(self, product_service: ProductService, product: Product):
        result = product_service.get_contracts(product.id)

        assert result == product.contracts

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_get_contracts_from_non_existent_product(self, product_service: ProductService):
        product_service.get_contracts(1337)

    def test_get_contract(self, product_service: ProductService, product: Product):
        result = product_service.get_contract(product.id, product.contracts[0].id)

        assert result == product.contracts[0]

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_get_contract_non_existent(self, product_service: ProductService, product: Product):
        product_service.get_contract(product.id, contract_id=1337)

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_get_contract_from_non_existent_product(self, product_service: ProductService):
        product_service.get_contract(1337, contract_id=1337)

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_get_contract_from_product_with_no_contracts(
        self, product_service: ProductService, team: Team
    ):
        product = product_service.create_product(
            data={"type": "D", "team_id": team.id}, scopes=[team.scope]
        )
        product_service.get_contract(product.id, contract_id=1337)

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_get_contract_from_other_product(
        self, product_service: ProductService, product: Product, team: Team
    ):
        new_product = product_service.create_product(
            data={"type": "D", "team_id": team.id}, scopes=[team.scope]
        )
        product_service.get_contract(new_product.id, product.contracts[0].id)

    def test_create_contract(self, product_service: ProductService, product: Product, team: Team):
        contract = product_service.create_contract(
            product_id=product.id, data={"publication_status": "D"}, scopes=[team.scope]
        )

        assert isinstance(contract, DataContract)
        assert len(product_service.get_contracts(product.id)) == 2

    @pytest.mark.parametrize(
        "data,missing_fields",
        [
            ({}, r"\[name, type, privacy_level\]"),
            ({"name": "Product"}, r"\[type, privacy_level\]"),
            ({"type": "D"}, r"\[name, privacy_level\]"),
            ({"privacy_level": "NPI"}, r"\[name, type\]"),
        ],
    )
    def test_create_contract_missing_fields(
        self, data, missing_fields, auth_service, product_service: ProductService, team
    ):
        """Test to see if a contract cannot be created when the product is missing necessary
        fields."""
        product = product_service.create_product(
            data={"team_id": team.id, **data}, scopes=[team.scope]
        )
        with pytest.raises(ValidationError, match=missing_fields):
            product_service.create_contract(
                product_id=product.id, data={"publication_status": "D"}, scopes=[team.scope]
            )

    def test_create_contract_no_missing_fields(
        self, auth_service, product_service: ProductService, team: Team
    ):
        """Test whether a contract can be created when all necessary fields are present on the
        product."""
        product = product_service.create_product(
            data={"team_id": team.id, "name": "Product", "type": "D", "privacy_level": "PI"},
            scopes=[team.scope],
        )
        contract = product_service.create_contract(
            product_id=product.id, data={"publication_status": "D"}, scopes=[team.scope]
        )
        assert contract.publication_status == "D"

    @pytest.mark.xfail(raises=NotAuthorized)
    def test_create_contract_non_existent_product(
        self, product_service: ProductService, team: Team
    ):
        product_service.create_contract(
            product_id=1337, data={"publication_status": "D"}, scopes=[team.scope]
        )

    def test_update_contract(self, product_service: ProductService, product: Product, team: Team):
        result = product_service.update_contract(
            product_id=product.id,
            contract_id=product.contracts[0].id,
            data={"name": "behoud bomen"},
            scopes=[team.scope],
        )

        assert len(product_service.get_contracts(product.id)) == 1
        assert result.name == "behoud bomen"

    def test_update_contract_keep_distributions_intact(
        self, product_service: ProductService, product: Product, team: Team
    ):
        """Ensure that an update to the contract keeps distributions intact."""
        current_distributions = product.contracts[0].distributions
        result = product_service.update_contract(
            product_id=product.id,
            contract_id=product.contracts[0].id,
            data={"retainment_period": 1000},
            scopes=[team.scope],
        )

        assert result.distributions == current_distributions

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_update_contract_other_product(
        self, product_service: ProductService, product: Product, team: Team
    ):
        new_product = product_service.create_product(
            data={"type": "D", "team_id": team.id}, scopes=[team.scope]
        )
        product_service.update_contract(
            product_id=new_product.id,
            contract_id=product.contracts[0].id,
            data={"name": "behoud bomen"},
            scopes=[team.scope],
        )

    def test_delete_contract(self, product_service: ProductService, product: Product, team: Team):
        product_service.delete_contract(
            product_id=product.id, contract_id=product.contracts[0].id, scopes=[team.scope]
        )

        assert len(product_service.get_contracts(product.id)) == 0

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_delete_contract_non_existent(
        self, product_service: ProductService, product: Product, team: Team
    ):
        product_service.delete_contract(
            product_id=product.id, contract_id=1337, scopes=[team.scope]
        )

    @pytest.mark.xfail(raises=NotAuthorized)
    def test_delete_contract_non_existent_product(
        self, product_service: ProductService, product: Product, team: Team
    ):
        product_service.delete_contract(
            product_id=1337, contract_id=product.contracts[0].id, scopes=[team.scope]
        )

    @pytest.mark.parametrize(
        "data,updated_status",
        [
            ({"publication_status": "P"}, "P"),
            ({"publication_status": "D"}, "D"),
        ],
    )
    def test_update_product_publication(
        self, data, updated_status, product_service: ProductService, product: Product, team: Team
    ):
        """Test to see if a product's publication status is updated accordingly."""
        result = product_service.update_publication_status(
            product_id=product.id, data=data, scopes=[team.scope]
        )

        assert result.publication_status == updated_status

    def test_update_product_publication_missing_fields(
        self, product_service: ProductService, team
    ):
        """Test to see if a product's publication status cannot be updated to published
        when the product is missing necessary fields."""

        data = {
            "name": "Product",
            "description": "Description of product",
            "language": "NL",
            "is_geo": True,
            "crs": "RD",
            "themes": ["NM"],
            "privacy_level": "NPI",
        }
        missing_fields = r"\[schema_url, refresh_period, contact_email\]"
        product_missing_fields = product_service.create_product(
            data={"team_id": team.id, **data}, scopes=[team.scope]
        )
        with pytest.raises(ValidationError, match=missing_fields):
            product_service.update_publication_status(
                product_id=product_missing_fields.id,
                data={"publication_status": "P"},
                scopes=[team.scope],
            )

    def test_allow_status_when_missing_fields(self, product_service: ProductService, team):
        """Test to see if a product's publication status can be updated to draft
        when the product is missing necessary fields."""

        data = {
            "name": "Product",
            "description": "Description of product",
            "language": "NL",
            "is_geo": True,
            "crs": "RD",
            "themes": ["NM"],
            "privacy_level": "NPI",
        }
        product_missing_fields = product_service.create_product(
            data={"team_id": team.id, **data}, scopes=[team.scope]
        )

        # This should not fail
        updated_product = product_service.update_publication_status(
            product_id=product_missing_fields.id,
            data={"publication_status": "D"},
            scopes=[team.scope],
        )

        assert updated_product.publication_status == "D"

    def test_get_distributions(self, product_service: ProductService, product: Product):
        result = product_service.get_distributions(
            product_id=product.id, contract_id=product.contracts[0].id
        )
        assert result == product.contracts[0].distributions

    def test_get_distribution(self, product_service: ProductService, product: Product):
        result = product_service.get_distribution(
            product_id=product.id,
            contract_id=product.contracts[0].id,
            distribution_id=product.contracts[0].distributions[0].id,
        )
        assert result == product.contracts[0].distributions[0]

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_get_distribution_non_existent(
        self, product_service: ProductService, product: Product
    ):
        product_service.get_distribution(
            product_id=product.id, contract_id=product.contracts[0].id, distribution_id=1337
        )

    def test_create_distribution(
        self, product_service: ProductService, product: Product, team: Team
    ):
        data = {"format": "TEST", "type": "F", "filename": "file.test"}
        distribution = product_service.create_distribution(
            product_id=product.id,
            contract_id=product.contracts[0].id,
            data=data,
            scopes=[team.scope],
        )
        updated_product = product_service.get_product(product.id)
        saved_distribution = updated_product.get_distribution(
            contract_id=product.contracts[0].id, distribution_id=distribution.id
        )
        assert saved_distribution.format == "TEST"
        assert saved_distribution.filename == "file.test"

    @pytest.mark.xfail(raises=NotAuthorized)
    def test_create_distribution_not_allowed(
        self, product_service: ProductService, product: Product
    ):
        data = {"format": "TEST", "type": "F"}
        product_service.create_distribution(
            product_id=product.id,
            contract_id=product.contracts[0].id,
            data=data,
            scopes=[],
        )

    def test_update_distribution(
        self, product_service: ProductService, product: Product, team: Team
    ):
        contract_id = product.contracts[0].id
        distribution_id = product.contracts[0].distributions[1].id
        data = {"format": "TEST", "type": "F"}
        product_service.update_distribution(
            product_id=product.id,
            contract_id=contract_id,
            distribution_id=distribution_id,
            data=data,
            scopes=[team.scope],
        )
        updated_distribution = product_service.get_product(product.id).get_distribution(
            contract_id, distribution_id
        )
        assert updated_distribution.format == "TEST"

    @pytest.mark.xfail(raises=NotAuthorized)
    def test_update_distribution_not_allowed(
        self, product_service: ProductService, product: Product
    ):
        data = {"format": "TEST", "type": "F"}
        product_service.update_distribution(
            product_id=product.id,
            contract_id=product.contracts[0].id,
            distribution_id=product.contracts[0].distributions[1].id,
            data=data,
            scopes=[],
        )

    def test_delete_distribution(
        self, product_service: ProductService, product: Product, team: Team
    ):
        contract_id = product.contracts[0].id
        distribution_id = product.contracts[0].distributions[1].id
        product_service.delete_distribution(
            product_id=product.id,
            contract_id=contract_id,
            distribution_id=distribution_id,
            scopes=[team.scope],
        )
        product = product_service.get_product(product_id=product.id)
        distribution_ids = [d.id for d in product.contracts[0].distributions]
        assert distribution_id not in distribution_ids

    @pytest.mark.xfail(raises=NotAuthorized)
    def test_delete_distribution_not_allowed(
        self, product_service: ProductService, product: Product
    ):
        contract_id = product.contracts[0].id
        distribution_id = product.contracts[0].distributions[1].id
        product_service.delete_distribution(
            product_id=product.id,
            contract_id=contract_id,
            distribution_id=distribution_id,
            scopes=[],
        )

    def test_get_services(self, product_service: ProductService, product: Product):
        result = product_service.get_services(product.id)

        assert result == product.services

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_get_services_from_non_existent_product(self, product_service: ProductService):
        product_service.get_services(1337)

    def test_get_service(self, product_service: ProductService, product: Product):
        result = product_service.get_service(product.id, product.services[0].id)

        assert result == product.services[0]

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_get_service_non_existent(self, product_service: ProductService, product: Product):
        product_service.get_service(product.id, service_id=1337)

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_get_service_from_non_existent_product(self, product_service: ProductService):
        product_service.get_service(1337, service_id=1337)

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_get_service_from_product_with_no_services(
        self, product_service: ProductService, team: Team
    ):
        product = product_service.create_product(
            data={"type": "D", "team_id": team.id}, scopes=[team.scope]
        )
        product_service.get_service(product.id, service_id=1337)

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_get_service_from_other_product(
        self, product_service: ProductService, product: Product, team: Team
    ):
        new_product = product_service.create_product(
            data={"type": "D", "team_id": team.id}, scopes=[team.scope]
        )
        product_service.get_service(new_product.id, product.services[0].id)

    def test_create_service(self, product_service: ProductService, product: Product, team: Team):
        result = product_service.create_service(
            product_id=product.id, data={"type": "WMS"}, scopes=[team.scope]
        )

        assert isinstance(result, DataService)
        assert len(product_service.get_services(product.id)) == 2

    @pytest.mark.xfail(raises=NotAuthorized)
    def test_create_service_non_existent_product(
        self, product_service: ProductService, team: Team
    ):
        product_service.create_service(product_id=1337, data={"type": "WMS"}, scopes=[team.scope])

    def test_update_service(self, product_service: ProductService, product: Product, team: Team):
        result = product_service.update_service(
            product_id=product.id,
            service_id=product.services[0].id,
            data={"type": "WMS"},
            scopes=[team.scope],
        )

        assert len(product_service.get_services(product.id)) == 1
        assert result.type == "WMS"

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_update_service_other_product(
        self, product_service: ProductService, product: Product, team: Team
    ):
        new_product = product_service.create_product(
            data={"type": "D", "team_id": team.id}, scopes=[team.scope]
        )
        product_service.update_service(
            product_id=new_product.id,
            service_id=product.services[0].id,
            data={"name": "behoud bomen"},
            scopes=[team.scope],
        )

    def test_delete_service(self, product_service, product: Product, team: Team):
        product.contracts = []
        product_service.delete_service(
            product_id=product.id, service_id=product.services[0].id, scopes=[team.scope]
        )

        assert len(product_service.get_services(product.id)) == 0

    @pytest.mark.xfail(raises=ValidationError)
    def test_delete_service_fails_when_distribution_accesses_it(
        self, product_service: ProductService, product: Product, team: Team
    ):
        product_service.delete_service(
            product_id=product.id, service_id=product.services[0].id, scopes=[team.scope]
        )

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_delete_service_non_existent(
        self, product_service: ProductService, product: Product, team: Team
    ):
        product_service.delete_service(product_id=product.id, service_id=1337, scopes=[team.scope])

    @pytest.mark.xfail(raises=NotAuthorized)
    def test_delete_service_non_existent_product(
        self, product_service: ProductService, product: Product, team: Team
    ):
        product_service.delete_service(
            product_id=1337, service_id=product.services[0].id, scopes=[team.scope]
        )
