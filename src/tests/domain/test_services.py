import pytest
from django.conf import settings

from domain.auth import AuthorizationService
from domain.exceptions import IllegalOperation, NotAuthorized, ObjectDoesNotExist
from domain.product import DataContract, DataService, ProductService
from domain.team import TeamService
from tests.domain.utils import DummyAuthRepo, DummyRepository

ADMIN_SCOPE = [settings.ADMIN_ROLE_NAME]
UNAUTHORIZED = ["unauthorized_scope"]
TEAM_BOR = ["scope_bor"]


class TestTeamService:
    def get_service(self, team=None):
        team_collection = []
        if team is not None:
            if isinstance(team, list):
                team_collection.extend(team)
            else:
                team_collection.append(team)
        auth_service = AuthorizationService(DummyAuthRepo(team_collection, products=[]))
        return TeamService(DummyRepository(team_collection), auth=auth_service)

    def test_get_team(self, team):
        service = self.get_service(team)
        result = service.get_team(team.id)

        assert result == team

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_get_team_non_existent(self, team):
        service = self.get_service(team)
        service.get_team(1337)  # non-existent id

    def test_get_teams(self, team):
        service = self.get_service(team)
        result = service.get_teams()

        assert result == [team]

    def test_create_team_by_admin(self):
        team_data = {
            "name": "Beheer Openbare Ruimte",
            "acronym": "BOR",
            "description": "",
            "po_name": "Jan Bor",
            "po_email": "j.bor@amsterdam.nl",
            "contact_email": "bor@amsterdam.nl",
            "scope": "scope_bor",
        }
        service = self.get_service()
        result = service.create_team(data=team_data, scopes=ADMIN_SCOPE)

        assert result.acronym == "BOR"
        assert len(service.get_teams()) == 1

    @pytest.mark.parametrize(
        "scopes",
        [pytest.param(UNAUTHORIZED, id="Unauthorized"), pytest.param(TEAM_BOR, id="Team Scope")],
    )
    @pytest.mark.xfail(raises=NotAuthorized)
    def test_create_team_unauthorized(self, scopes):
        team_data = {
            "name": "Beheer Openbare Ruimte",
            "acronym": "BOR",
            "description": "",
            "po_name": "Jan Bor",
            "po_email": "j.bor@amsterdam.nl",
            "contact_email": "bor@amsterdam.nl",
            "scope": "scope_bor",
        }
        service = self.get_service()
        service.create_team(data=team_data, scopes=scopes)

    @pytest.mark.xfail(raises=IllegalOperation)
    def test_create_team_with_id(self):
        team_data = {
            "id": 2,
            "name": "Beheer Openbare Ruimte",
            "acronym": "BOR",
            "description": "",
            "po_name": "Jan Bor",
            "po_email": "j.bor@amsterdam.nl",
            "contact_email": "bor@amsterdam.nl",
            "scope": "scope_bor",
        }
        service = self.get_service()
        service.create_team(data=team_data, scopes=ADMIN_SCOPE)

    def test_update_team(self, team):
        service = self.get_service(team)
        service.update_team(
            team_id=team.id, data={"description": "New Description"}, scopes=ADMIN_SCOPE
        )

        result = service.get_team(team.id)
        assert result.description == "New Description"

    @pytest.mark.xfail(raises=NotAuthorized)
    def test_update_team_unauthorized_field(self, team):
        service = self.get_service(team)
        service.update_team(
            team_id=team.id, data={"description": "New Description"}, scopes={team.scope}
        )

    def test_update_team_by_team_member(self, team):
        service = self.get_service(team)
        service.update_team(
            team_id=team.id,
            data={
                "po_name": "Someone Else",
                "po_email": "s.else@amsterdam.nl",
                "contact_email": "new.email@amsterdam.nl",
            },
            scopes={team.scope},
        )

        result = service.get_team(team.id)
        assert result.po_name == "Someone Else"
        assert result.po_email == "s.else@amsterdam.nl"
        assert result.contact_email == "new.email@amsterdam.nl"

    @pytest.mark.xfail(raises=NotAuthorized)
    def test_update_team_by_other_team_unauthorized(self, team, other_team):
        service = self.get_service(team=[team, other_team])
        service.update_team(
            team_id=team.id,
            data={
                "po_name": "Someone Else",
                "po_email": "s.else@amsterdam.nl",
                "contact_email": "new.email@amsterdam.nl",
            },
            scopes={other_team.scope},
        )

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_update_team_non_existent(self, team):
        service = self.get_service(team)
        service.update_team(
            team_id=1337, data={"description": "New Description"}, scopes=ADMIN_SCOPE
        )

    @pytest.mark.xfail(raises=IllegalOperation)
    def test_update_team_cannot_update_id(self, team):
        service = self.get_service(team)
        service.update_team(team_id=team.id, data={"id": 1337}, scopes=ADMIN_SCOPE)

    def test_delete_team_by_admin(self, team):
        service = self.get_service(team)
        service.delete_team(team_id=team.id, scopes=ADMIN_SCOPE)

        assert len(service.get_teams()) == 0

    @pytest.mark.xfail(raises=NotAuthorized)
    def test_delete_team_unauthorized(self, team):
        service = self.get_service(team)
        service.delete_team(team_id=team.id, scopes=UNAUTHORIZED)

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_delete_team_non_existent(self, team):
        service = self.get_service(team)
        service.delete_team(team_id=1337, scopes=ADMIN_SCOPE)  # non-existent


class TestProductService:
    def get_service(self, product=None, team=None) -> ProductService:
        """Returns a service connected to a repo with 0 or 1 products."""
        team_collection = []
        if team is not None:
            if isinstance(team, list):
                team_collection.extend(team)
            else:
                team_collection.append(team)
        product_collection = []
        if product is not None:
            if isinstance(product, list):
                product_collection.extend(product)
            else:
                product_collection.append(product)
        auth_repo = DummyAuthRepo(team_collection, product_collection)
        auth = AuthorizationService(repo=auth_repo)
        return ProductService(repo=DummyRepository(product_collection), auth=auth)

    def test_get_products(self, product):
        service = self.get_service(product)
        result = service.get_products()

        assert result == [product]

    def test_get_product(self, product):
        service = self.get_service(product)
        result = service.get_product(product.id)

        assert result == product

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_get_product_non_existent(self, product):
        service = self.get_service(product)
        service.get_product(1337)  # non-existent

    def test_create_product(self, team):
        service = self.get_service(team=team)
        data = {"type": "D", "publication_status": "D", "team_id": team.id}
        result = service.create_product(data=data, scopes=[team.scope])

        assert len(service.get_products()) == 1
        assert result.type == "D"

    @pytest.mark.xfail(raises=NotAuthorized)
    def test_create_product_other_team(self, team, other_team):
        service = self.get_service(team=[team, other_team])
        data = {"type": "D", "publication_status": "D", "team_id": other_team.id}
        service.create_product(data=data, scopes=[team.scope])

    @pytest.mark.xfail(raises=IllegalOperation)
    def test_create_product_with_id(self, team):
        service = self.get_service(team=team)
        data = {"id": 1337, "type": "D", "publication_status": "D", "team_id": team.id}
        service.create_product(data=data, scopes=[team.scope])

    def test_update_product(self, product, team):
        service = self.get_service(product, team)
        data = {"description": "a fancy product"}
        service.update_product(product_id=product.id, data=data, scopes=team.scope)

        result = service.get_product(product.id)

        assert result.description == "a fancy product"

    @pytest.mark.xfail(raises=NotAuthorized)
    def test_update_product_non_existent(self, product, team):
        service = self.get_service(product, team)
        data = {"description": "a fancy product"}
        service.update_product(product_id=1337, data=data, scopes=team.scope)

    @pytest.mark.xfail(raises=IllegalOperation)
    def test_update_product_cannot_update_id(self, product, team):
        service = self.get_service(product, team)
        service.update_product(product_id=product.id, data={"id": 1337}, scopes=team.scope)

    def test_delete_product(self, product, team):
        service = self.get_service(product, team)
        service.delete_product(product_id=product.id, scopes=team.scope)

        assert len(service.get_products()) == 0

    @pytest.mark.xfail(raises=NotAuthorized)
    def test_delete_product_non_existent(self, product, team):
        service = self.get_service(product, team)
        service.delete_product(product_id=1337, scopes=team.scope)  # non-existent

    def test_get_contracts(self, product):
        service = self.get_service(product)
        result = service.get_contracts(product.id)

        assert result == product.contracts

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_get_contracts_from_non_existent_product(self, product):
        service = self.get_service(product)
        service.get_contracts(1337)

    def test_get_contract(self, product):
        service = self.get_service(product)
        result = service.get_contract(product.id, product.contracts[0].id)

        assert result == product.contracts[0]

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_get_contract_non_existent(self, product):
        service = self.get_service(product)
        service.get_contract(product.id, contract_id=1337)

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_get_contract_from_non_existent_product(self, product):
        service = self.get_service(product)
        service.get_contract(1337, contract_id=1337)

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_get_contract_from_product_with_no_contracts(self, team):
        service = self.get_service(team=team)
        product = service.create_product(
            data={"type": "D", "team_id": team.id}, scopes=[team.scope]
        )
        service.get_contract(product.id, contract_id=1337)

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_get_contract_from_other_product(self, product, team):
        service = self.get_service(product, team)
        new_product = service.create_product(
            data={"type": "D", "team_id": team.id}, scopes=[team.scope]
        )
        service.get_contract(new_product.id, product.contracts[0].id)

    def test_create_contract(self, product, team):
        service = self.get_service(product, team)
        contract = service.create_contract(
            product_id=product.id, data={"publication_status": "D"}, scopes=[team.scope]
        )

        assert isinstance(contract, DataContract)
        assert len(service.get_contracts(product.id)) == 2

    @pytest.mark.xfail(raises=IllegalOperation)
    def test_create_contract_with_id(self, product, team):
        service = self.get_service(product, team)
        service.create_contract(
            product_id=product.id, data={"id": 2, "publication_status": "D"}, scopes=[team.scope]
        )

    @pytest.mark.xfail(raises=NotAuthorized)
    def test_create_contract_non_existent_product(self, team):
        service = self.get_service(team=team)
        service.create_contract(
            product_id=1337, data={"publication_status": "D"}, scopes=[team.scope]
        )

    def test_update_contract(self, product, team):
        service = self.get_service(product, team)
        result = service.update_contract(
            product_id=product.id,
            contract_id=product.contracts[0].id,
            data={"name": "behoud bomen"},
            scopes=[team.scope],
        )

        assert len(service.get_contracts(product.id)) == 1
        assert result.name == "behoud bomen"

    @pytest.mark.xfail(raises=IllegalOperation)
    def test_update_contract_with_id(self, product, team):
        service = self.get_service(product, team)
        service.update_contract(
            product_id=product.id,
            contract_id=product.contracts[0].id,
            data={"id": 2},
            scopes=[team.scope],
        )

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_update_contract_other_product(self, product, team):
        service = self.get_service(product, team)
        new_product = service.create_product(
            data={"type": "D", "team_id": team.id}, scopes=[team.scope]
        )
        service.update_contract(
            product_id=new_product.id,
            contract_id=product.contracts[0].id,
            data={"name": "behoud bomen"},
            scopes=[team.scope],
        )

    def test_delete_contract(self, product, team):
        service = self.get_service(product, team)
        service.delete_contract(
            product_id=product.id, contract_id=product.contracts[0].id, scopes=[team.scope]
        )

        assert len(service.get_contracts(product.id)) == 0

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_delete_contract_non_existent(self, product, team):
        service = self.get_service(product, team)
        service.delete_contract(product_id=product.id, contract_id=1337, scopes=[team.scope])

    @pytest.mark.xfail(raises=NotAuthorized)
    def test_delete_contract_non_existent_product(self, product, team):
        service = self.get_service(product, team)
        service.delete_contract(
            product_id=1337, contract_id=product.contracts[0].id, scopes=[team.scope]
        )

    def test_get_services(self, product):
        service = self.get_service(product)
        result = service.get_services(product.id)

        assert result == product.services

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_get_services_from_non_existent_product(self, product):
        service = self.get_service(product)
        service.get_services(1337)

    def test_get_service(self, product):
        service = self.get_service(product)
        result = service.get_service(product.id, product.services[0].id)

        assert result == product.services[0]

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_get_service_non_existent(self, product):
        service = self.get_service(product)
        service.get_service(product.id, service_id=1337)

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_get_service_from_non_existent_product(self, product):
        service = self.get_service(product)
        service.get_service(1337, service_id=1337)

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_get_service_from_product_with_no_services(self, team):
        service = self.get_service(team=team)
        product = service.create_product(
            data={"type": "D", "team_id": team.id}, scopes=[team.scope]
        )
        service.get_service(product.id, service_id=1337)

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_get_service_from_other_product(self, product, team):
        service = self.get_service(product, team)
        new_product = service.create_product(
            data={"type": "D", "team_id": team.id}, scopes=[team.scope]
        )
        service.get_service(new_product.id, product.services[0].id)

    def test_create_service(self, product, team):
        service = self.get_service(product, team)
        result = service.create_service(
            product_id=product.id, data={"type": "WMS"}, scopes=[team.scope]
        )

        assert isinstance(result, DataService)
        assert len(service.get_services(product.id)) == 2

    @pytest.mark.xfail(raises=IllegalOperation)
    def test_create_service_with_id(self, product, team):
        service = self.get_service(product, team)
        service.create_service(
            product_id=product.id, data={"id": 2, "type": "WMS"}, scopes=[team.scope]
        )

    @pytest.mark.xfail(raises=NotAuthorized)
    def test_create_service_non_existent_product(self, team):
        service = self.get_service(team=team)
        service.create_service(product_id=1337, data={"type": "WMS"}, scopes=[team.scope])

    def test_update_service(self, product, team):
        service = self.get_service(product, team)
        result = service.update_service(
            product_id=product.id,
            service_id=product.services[0].id,
            data={"type": "WMS"},
            scopes=[team.scope],
        )

        assert len(service.get_services(product.id)) == 1
        assert result.type == "WMS"

    @pytest.mark.xfail(raises=IllegalOperation)
    def test_update_service_with_id(self, product, team):
        service = self.get_service(product, team)
        service.update_service(
            product_id=product.id,
            service_id=product.services[0].id,
            data={"id": 2},
            scopes=[team.scope],
        )

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_update_service_other_product(self, product, team):
        service = self.get_service(product, team)
        new_product = service.create_product(
            data={"type": "D", "team_id": team.id}, scopes=[team.scope]
        )
        service.update_service(
            product_id=new_product.id,
            service_id=product.services[0].id,
            data={"name": "behoud bomen"},
            scopes=[team.scope],
        )

    def test_delete_service(self, product, team):
        service = self.get_service(product, team)
        service.delete_service(
            product_id=product.id, service_id=product.services[0].id, scopes=[team.scope]
        )

        assert len(service.get_services(product.id)) == 0

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_delete_service_non_existent(self, product, team):
        service = self.get_service(product, team)
        service.delete_service(product_id=product.id, service_id=1337, scopes=[team.scope])

    @pytest.mark.xfail(raises=NotAuthorized)
    def test_delete_service_non_existent_product(self, product, team):
        service = self.get_service(product, team)
        service.delete_service(
            product_id=1337, service_id=product.services[0].id, scopes=[team.scope]
        )
