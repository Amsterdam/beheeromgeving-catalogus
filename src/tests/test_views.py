import pytest
from django.conf import settings

from beheeromgeving.models import Team
from tests.utils import build_jwt_token


def test_health(api_client):
    response = api_client.get("/pulse")
    assert response.status_code == 200
    assert response.data == {"status": "OK"}


@pytest.mark.django_db
class TestViews:

    @pytest.mark.parametrize(
        "path",
        [
            "/products/1337",
            "/products/1337/contracts",
            "/products/1337/contracts/1337",
            "/products/1337/services",
            "/products/1337/services/1337",
            "/teams/1337",
        ],
    )
    def test_404(self, api_client, path):
        response = api_client.get(path)
        assert response.status_code == 404

    def test_teams_list(self, api_client, orm_team):
        response = api_client.get("/teams")
        assert response.status_code == 200
        assert response.data[0]["acronym"] == "DADI"

    def test_teams_detail(self, api_client, orm_team):
        response = api_client.get("/teams")
        response = api_client.get(f"/teams/{orm_team.id}")
        assert response.status_code == 200
        assert response.data["acronym"] == "DADI"

    def test_teams_create_by_admin(self, api_client):
        token = build_jwt_token([settings.ADMIN_ROLE_NAME])
        response = api_client.post(
            "/teams",
            data={
                "name": "Basis- en Kernregistratie",
                "description": "Beschrijving",
                "acronym": "BENK",
                "po_name": "Iemand",
                "po_email": "iemand@amsterdam.nl",
                "contact_email": "benk@amsterdam.nl",
                "scope": "scope_benk",
            },
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code == 201
        result = api_client.get(f"/teams/{response.data}")
        assert result.data["acronym"] == "BENK"

    def test_teams_create_unauthorized(self, api_client):
        token = build_jwt_token(["some_unauthorized_scope"])
        response = api_client.post(
            "/teams",
            data={
                "name": "Basis- en Kernregistratie",
                "description": "Beschrijving",
                "acronym": "BENK",
                "po_name": "Iemand",
                "po_email": "iemand@amsterdam.nl",
                "contact_email": "benk@amsterdam.nl",
                "scope": "scope_benk",
            },
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code == 401
        # No team created
        result = api_client.get("/teams")
        assert len(result.data) == 0

    def test_teams_update(self, api_client, orm_team):
        response = api_client.patch(
            f"/teams/{orm_team.id}",
            data={
                "po_name": "Iemand Anders",
            },
        )
        assert response.status_code == 200

        orm_team.refresh_from_db()
        assert orm_team.po_name == "Iemand Anders"

    def test_teams_delete_by_admin(self, api_client, orm_team):
        token = build_jwt_token([settings.ADMIN_ROLE_NAME])
        response = api_client.delete(f"/teams/{orm_team.id}", HTTP_AUTHORIZATION=f"Bearer {token}")
        assert response.status_code == 204
        assert Team.objects.count() == 0

    def test_teams_delete_unauthorized(self, api_client, orm_team):
        token = build_jwt_token(["some_unauthorized_scope"])
        response = api_client.delete(f"/teams/{orm_team.id}", HTTP_AUTHORIZATION=f"Bearer {token}")
        assert response.status_code == 401
        assert Team.objects.count() == 1

    def test_products_list(self, api_client, orm_product):
        response = api_client.get("/products")
        assert response.status_code == 200
        assert response.data[0]["name"] == orm_product.name

    def test_product_detail(self, api_client, orm_product):
        response = api_client.get(f"/products/{orm_product.id}")
        assert response.status_code == 200
        assert response.data["name"] == "bomen"

    def test_product_create(self, api_client, orm_team):
        response = api_client.post("/products", data={"type": "D", "team_id": orm_team.id})
        assert response.status_code == 201

    @pytest.mark.parametrize(
        "data",
        [
            {"id": 1337},  # Cannot set id
            {"refresh_period": 2},  # Wrong type
        ],
    )
    def test_product_create_bad_data(self, api_client, data, orm_team):
        response = api_client.post("/products", data={**data, "team_id": orm_team.id})
        assert response.status_code == 400

    def test_product_update(self, api_client, orm_product):
        response = api_client.patch(
            f"/products/{orm_product.id}", data={"refresh_period": "2 maanden"}
        )
        assert response.status_code == 200

    def test_contract_list(self, api_client, orm_product):
        response = api_client.get(f"/products/{orm_product.id}/contracts")

        assert response.status_code == 200
        assert len(response.data) == 1

    def test_contract_create(self, api_client, orm_product):
        response = api_client.post(
            f"/products/{orm_product.id}/contracts", data={"name": "contract1"}
        )
        assert response.status_code == 201

    def test_contract_update(self, api_client, orm_product):
        contract_id = orm_product.contracts.first().id
        response = api_client.patch(
            f"/products/{orm_product.id}/contracts/{contract_id}", data={"name": "contract1"}
        )
        assert response.status_code == 200

    @pytest.mark.parametrize(
        "data",
        [
            {"id": 1337},  # Cannot set id
            {"name": 2},  # Wrong type
            {"distributions": [{"type": 3}]},  # Wrong type on subfield
        ],
    )
    def test_contract_update_bad_data(self, api_client, data, orm_product):
        contract_id = orm_product.contracts.first().id
        response = api_client.patch(
            f"/products/{orm_product.id}/contracts/{contract_id}", data=data
        )
        assert response.status_code == 400

    def test_contract_delete(self, api_client, orm_product):
        contract_id = orm_product.contracts.first().id
        response = api_client.delete(f"/products/{orm_product.id}/contracts/{contract_id}")

        assert response.status_code == 204

    def test_service_list(self, api_client, orm_product):
        response = api_client.get(f"/products/{orm_product.id}/services")

        assert response.status_code == 200
        assert len(response.data) == 1

    def test_service_create(self, api_client, orm_product):
        response = api_client.post(
            f"/products/{orm_product.id}/services",
            data={"type": "REST", "endpoint_url": "https://api.data.amsterdam.nl/v1/bomen/v2"},
        )
        assert response.status_code == 201

    def test_service_update(self, api_client, orm_product):
        service_id = orm_product.services.first().id
        response = api_client.patch(
            f"/products/{orm_product.id}/services/{service_id}", data={"type": "WMS"}
        )
        assert response.status_code == 200

    @pytest.mark.parametrize(
        "data",
        [
            {"id": 1337},  # Cannot set id
            {"type": "API"},  # Wrong type
        ],
    )
    def test_service_update_bad_data(self, api_client, data, orm_product):
        service_id = orm_product.services.first().id
        response = api_client.patch(f"/products/{orm_product.id}/services/{service_id}", data=data)
        assert response.status_code == 400

    def test_service_delete(self, api_client, orm_product):
        service_id = orm_product.services.first().id
        response = api_client.delete(f"/products/{orm_product.id}/services/{service_id}")

        assert response.status_code == 204
