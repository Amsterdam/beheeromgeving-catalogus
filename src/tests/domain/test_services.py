import pytest
from django.conf import settings

from domain.exceptions import IllegalOperation, NotAuthorized, ObjectDoesNotExist
from domain.product.objects import DataContract, DataService
from domain.product.services import ProductService, TeamService
from tests.domain.utils import DummyRepository

ADMIN_SCOPES = [settings.ADMIN_ROLE_NAME]
UNAUTHORIZED = ["unauthorized_scope"]


class TestTeamService:
    def get_service(self, team=None):
        return TeamService(
            DummyRepository([team] if team else []), admin_role=settings.ADMIN_ROLE_NAME
        )

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
        result = service.create_team(team_data, scopes=ADMIN_SCOPES)

        assert result.acronym == "BOR"
        assert len(service.get_teams()) == 1

    @pytest.mark.xfail(raises=NotAuthorized)
    def test_create_team_unauthorized(self):
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
        service.create_team(team_data, scopes=UNAUTHORIZED)

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
        service.create_team(team_data, scopes=ADMIN_SCOPES)

    def test_update_team(self, team):
        service = self.get_service(team)
        service.update_team(team.id, {"description": "New Description"})

        result = service.get_team(team.id)
        assert result.description == "New Description"

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_update_team_non_existent(self, team):
        service = self.get_service(team)
        service.update_team(1337, {"description": "New Description"})

    @pytest.mark.xfail(raises=IllegalOperation)
    def test_update_team_cannot_update_id(self, team):
        service = self.get_service(team)
        service.update_team(team.id, {"id": 1337})

    def test_delete_team_by_admin(self, team):
        service = self.get_service(team)
        service.delete_team(team.id, scopes=ADMIN_SCOPES)

        assert len(service.get_teams()) == 0

    @pytest.mark.xfail(raises=NotAuthorized)
    def test_delete_team_unauthorized(self, team):
        service = self.get_service(team)
        service.delete_team(team.id, scopes=UNAUTHORIZED)

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_delete_team_non_existent(self, team):
        service = self.get_service(team)
        service.delete_team(1337, scopes=ADMIN_SCOPES)  # non-existent


class TestProductService:
    def get_service(self, product=None) -> ProductService:
        """Returns a service connected to a repo with 0 or 1 products."""
        return ProductService(DummyRepository([product] if product else []))

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

    def test_create_product(self):
        service = self.get_service()
        data = {"type": "D", "publication_status": "D"}
        result = service.create_product(data)

        assert len(service.get_products()) == 1
        assert result.type == "D"

    @pytest.mark.xfail(raises=IllegalOperation)
    def test_create_product_with_id(self):
        service = self.get_service()
        data = {"id": 1337, "type": "D", "publication_status": "D"}
        service.create_product(data)

    def test_update_product(self, product):
        service = self.get_service(product)
        data = {"description": "a fancy product"}
        service.update_product(product.id, data)

        result = service.get_product(product.id)

        assert result.description == "a fancy product"

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_update_product_non_existent(self, product):
        service = self.get_service(product)
        data = {"description": "a fancy product"}
        service.update_product(1337, data)

    @pytest.mark.xfail(raises=IllegalOperation)
    def test_update_product_cannot_update_id(self, product):
        service = self.get_service(product)
        service.update_product(product.id, {"id": 1337})

    def test_delete_product(self, product):
        service = self.get_service(product)
        service.delete_product(product.id)

        assert len(service.get_products()) == 0

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_delete_product_non_existent(self, product):
        service = self.get_service(product)
        service.delete_product(1337)  # non-existent

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
    def test_get_contract_from_product_with_no_contracts(self):
        service = self.get_service()
        product = service.create_product({"type": "D"})
        service.get_contract(product.id, contract_id=1337)

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_get_contract_from_other_product(self, product):
        service = self.get_service(product)
        new_product = service.create_product({"type": "D"})
        service.get_contract(new_product.id, product.contracts[0].id)

    def test_create_contract(self, product):
        service = self.get_service(product)
        contract = service.create_contract(product.id, {"publication_status": "D"})

        assert isinstance(contract, DataContract)
        assert len(service.get_contracts(product.id)) == 2

    @pytest.mark.xfail(raises=IllegalOperation)
    def test_create_contract_with_id(self, product):
        service = self.get_service(product)
        service.create_contract(product.id, {"id": 2, "publication_status": "D"})

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_create_contract_non_existent_product(self):
        service = self.get_service()
        service.create_contract(product_id=1337, contract_data={"publication_status": "D"})

    def test_update_contract(self, product):
        service = self.get_service(product)
        result = service.update_contract(
            product.id, product.contracts[0].id, {"name": "behoud bomen"}
        )

        assert len(service.get_contracts(product.id)) == 1
        assert result.name == "behoud bomen"

    @pytest.mark.xfail(raises=IllegalOperation)
    def test_update_contract_with_id(self, product):
        service = self.get_service(product)
        service.update_contract(product.id, product.contracts[0].id, {"id": 2})

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_update_contract_other_product(self, product):
        service = self.get_service(product)
        new_product = service.create_product({"type": "D"})
        service.update_contract(new_product.id, product.contracts[0].id, {"name": "behoud bomen"})

    def test_delete_contract(self, product):
        service = self.get_service(product)
        service.delete_contract(product.id, product.contracts[0].id)

        assert len(service.get_contracts(product.id)) == 0

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_delete_contract_non_existent(self, product):
        service = self.get_service(product)
        service.delete_contract(product.id, 1337)

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_delete_contract_non_existent_product(self, product):
        service = self.get_service(product)
        service.delete_contract(1337, product.contracts[0].id)

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
    def test_get_service_from_product_with_no_services(self):
        service = self.get_service()
        product = service.create_product({"type": "D"})
        service.get_service(product.id, service_id=1337)

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_get_service_from_other_product(self, product):
        service = self.get_service(product)
        new_product = service.create_product({"type": "D"})
        service.get_service(new_product.id, product.services[0].id)

    def test_create_service(self, product):
        service = self.get_service(product)
        result = service.create_service(product.id, {"type": "WMS"})

        assert isinstance(result, DataService)
        assert len(service.get_services(product.id)) == 2

    @pytest.mark.xfail(raises=IllegalOperation)
    def test_create_service_with_id(self, product):
        service = self.get_service(product)
        service.create_service(product.id, {"id": 2, "type": "WMS"})

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_create_service_non_existent_product(self):
        service = self.get_service()
        service.create_service(product_id=1337, service_data={"type": "WMS"})

    def test_update_service(self, product):
        service = self.get_service(product)
        result = service.update_service(product.id, product.services[0].id, {"type": "WMS"})

        assert len(service.get_services(product.id)) == 1
        assert result.type == "WMS"

    @pytest.mark.xfail(raises=IllegalOperation)
    def test_update_service_with_id(self, product):
        service = self.get_service(product)
        service.update_service(product.id, product.services[0].id, {"id": 2})

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_update_service_other_product(self, product):
        service = self.get_service(product)
        new_product = service.create_product({"type": "D"})
        service.update_service(new_product.id, product.services[0].id, {"name": "behoud bomen"})

    def test_delete_service(self, product):
        service = self.get_service(product)
        service.delete_service(product.id, product.services[0].id)

        assert len(service.get_services(product.id)) == 0

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_delete_service_non_existent(self, product):
        service = self.get_service(product)
        service.delete_service(product.id, 1337)

    @pytest.mark.xfail(raises=ObjectDoesNotExist)
    def test_delete_service_non_existent_product(self, product):
        service = self.get_service(product)
        service.delete_service(1337, product.services[0].id)
