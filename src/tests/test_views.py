import pytest
from django.conf import settings

from beheeromgeving.models import Team


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

    def test_teams_create_by_admin(self, client_with_token):
        response = client_with_token([settings.ADMIN_ROLE_NAME]).post(
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
        )
        assert response.status_code == 201
        result = client_with_token().get(f"/teams/{response.data}")
        assert result.data["acronym"] == "BENK"

    def test_teams_create_unauthorized(self, client_with_token):
        response = client_with_token(["some_unauthorized_scope"]).post(
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
        )
        assert response.status_code == 401
        # No team created
        result = client_with_token([]).get("/teams")
        assert len(result.data) == 0

    def test_teams_update(self, client_with_token, orm_team):
        response = client_with_token([settings.ADMIN_ROLE_NAME]).patch(
            f"/teams/{orm_team.id}",
            data={
                "po_name": "Iemand Anders",
            },
        )
        assert response.status_code == 200

        orm_team.refresh_from_db()
        assert orm_team.po_name == "Iemand Anders"

    def test_teams_delete_by_admin(self, client_with_token, orm_team):
        response = client_with_token([settings.ADMIN_ROLE_NAME]).delete(f"/teams/{orm_team.id}")
        assert response.status_code == 204
        assert Team.objects.count() == 0

    def test_teams_delete_unauthorized(self, client_with_token, orm_team):
        response = client_with_token(["some_unauthorized_scope"]).delete(f"/teams/{orm_team.id}")
        assert response.status_code == 401
        assert Team.objects.count() == 1

    def test_products_list(self, api_client, orm_product):
        response = api_client.get("/products")
        assert response.status_code == 200
        product = response.data[0]
        assert product["name"] == orm_product.name
        assert product["summary"] == {"distributions": ["F"], "services": ["REST"]}
        for key in [
            "description",
            "language",
            "owner",
            "type",
            "themes",
            "last_updated",
            "team_id",
            "contract_count",
            "publication_status",
        ]:
            assert key in product

    def test_product_detail(self, api_client, orm_product):
        response = api_client.get(f"/products/{orm_product.id}")
        assert response.status_code == 200
        assert response.data["name"] == "bomen"

    def test_product_create(self, client_with_token, orm_team):
        response = client_with_token([orm_team.scope]).post(
            "/products",
            data={"type": "D", "team_id": orm_team.id},
        )
        assert response.status_code == 201

    @pytest.mark.parametrize(
        "data",
        [
            {"refresh_period": 2},  # Wrong type
        ],
    )
    def test_product_create_bad_data(self, client_with_token, data, orm_team):
        response = client_with_token([orm_team.scope]).post(
            "/products",
            data={**data, "team_id": orm_team.id},
        )
        assert response.status_code == 400

    @pytest.mark.parametrize(
        "data",
        [
            # fields that can be updated
            {"name": "New Name"},
            {"description": "New Description"},
            {"language": "EN"},
            {"is_geo": True},
            {"crs": "RD"},
            {"schema_url": "https://schemas.data.amsterdam.nl/datasets/new_url"},
            {"type": "I"},
            {"privacy_level": "PI"},
            {"owner": "New Owner"},
            {"contact_email": "newmail@contact.nl"},
            {"data_steward": "newmail@steward.nl"},
        ],
    )
    def test_product_update(self, client_with_token, orm_product, orm_team, data):
        response = client_with_token([orm_team.scope]).patch(
            f"/products/{orm_product.id}",
            data=data,
        )
        assert response.status_code == 200
        orm_product.refresh_from_db()
        for key, val in data.items():
            assert response.data[key] == val
            assert getattr(orm_product, key) == val
        assert response.data["last_updated"] == orm_product.last_updated

    def test_product_update_refresh_period(self, client_with_token, orm_product, orm_team):
        data = {"refresh_period": {"unit": "MONTH", "frequency": 2}}
        response = client_with_token([orm_team.scope]).patch(
            f"/products/{orm_product.id}",
            data=data,
        )
        assert response.status_code == 200
        orm_product.refresh_from_db()
        assert orm_product.refresh_period == "2.MONTH"  # DB stores in this way.
        assert response.data["refresh_period"] == data["refresh_period"]
        assert response.data["last_updated"] == orm_product.last_updated

    @pytest.mark.parametrize(
        "data",
        [
            {"publication_status": "D"},
            {"publication_status": "P"},
        ],
    )
    def test_set_state_product(self, client_with_token, orm_product, orm_team, data):
        response = client_with_token([orm_team.scope]).post(
            f"/products/{orm_product.id}/set-state",
            data=data,
        )
        assert response.status_code == 200
        orm_product.refresh_from_db()

        assert orm_product.publication_status == data["publication_status"]
        assert response.data["publication_status"] == orm_product.publication_status

    def test_contract_list(self, api_client, orm_product):
        response = api_client.get(f"/products/{orm_product.id}/contracts")

        assert response.status_code == 200
        assert len(response.data) == 1

    def test_contract_create(self, client_with_token, orm_product, orm_team):
        response = client_with_token([orm_team.scope]).post(
            f"/products/{orm_product.id}/contracts",
            data={"name": "contract1"},
        )
        assert response.status_code == 201

    @pytest.mark.parametrize(
        "data",
        [
            # fields that can be updated
            {"name": "New Name"},
            {"purpose": "New Purpose"},
            {"description": "New Description"},
            {"privacy_level": "BI"},
            {"publication_status": "P"},
            {"contact_email": "new@email.address"},
            {"data_steward": "Someone Else"},
            {"scope": "another_scope"},
            {"confidentiality": "V"},
            {"start_date": "2025-02-02"},
            {"retainment_period": 100},
        ],
    )
    def test_contract_update(self, client_with_token, orm_product, orm_team, data):
        contract_id = orm_product.contracts.first().id
        response = client_with_token([orm_team.scope]).patch(
            f"/products/{orm_product.id}/contracts/{contract_id}", data=data
        )
        assert response.status_code == 200

    @pytest.mark.parametrize(
        "data",
        [
            {"name": 2},  # Wrong type
            {"distributions": [{"type": 3}]},  # Wrong type on subfield
        ],
    )
    def test_contract_update_bad_data(self, client_with_token, data, orm_product, orm_team):
        contract_id = orm_product.contracts.first().id
        response = client_with_token([orm_team.scope]).patch(
            f"/products/{orm_product.id}/contracts/{contract_id}", data=data
        )
        assert response.status_code == 400

    def test_contract_delete(self, client_with_token, orm_product, orm_team):
        contract_id = orm_product.contracts.first().id
        response = client_with_token([orm_team.scope]).delete(
            f"/products/{orm_product.id}/contracts/{contract_id}"
        )

        assert response.status_code == 204
        orm_product.refresh_from_db()

        assert len(orm_product.contracts.all()) == 0

    def test_distribution_list(self, api_client, orm_product):
        contract_id = orm_product.contracts.first().id
        response = api_client.get(
            f"/products/{orm_product.id}/contracts/{contract_id}/distributions"
        )
        assert response.status_code == 200
        assert len(response.data) == 2

    def test_distribution_detail(self, api_client, orm_product):
        contract_id = orm_product.contracts.first().id
        distribution_id = orm_product.contracts.first().distributions.first().id
        response = api_client.get(
            f"/products/{orm_product.id}/contracts/{contract_id}/distributions/{distribution_id}"
        )
        assert response.status_code == 200
        assert response.data["type"] == "A"  # API

    def test_distribution_detail_404(self, api_client, orm_product):
        contract_id = orm_product.contracts.first().id
        response = api_client.get(
            f"/products/{orm_product.id}/contracts/{contract_id}/distributions/1337"
        )
        assert response.status_code == 404

    def test_distribution_create(self, client_with_token, orm_product, orm_team):
        contract_id = orm_product.contracts.first().id
        data = {"format": "TEST", "type": "F"}
        response = client_with_token([orm_team.scope]).post(
            f"/products/{orm_product.id}/contracts/{contract_id}/distributions", data=data
        )
        assert response.status_code == 201

    def test_distribution_create_empty(self, client_with_token, orm_product, orm_team):
        contract_id = orm_product.contracts.first().id
        data = {}
        response = client_with_token([orm_team.scope]).post(
            f"/products/{orm_product.id}/contracts/{contract_id}/distributions", data=data
        )
        assert response.status_code == 201

    def test_distribution_create_not_allowed(self, client_with_token, orm_product, orm_other_team):
        contract_id = orm_product.contracts.first().id
        data = {"format": "TEST", "type": "F"}
        response = client_with_token([orm_other_team.scope]).post(
            f"/products/{orm_product.id}/contracts/{contract_id}/distributions", data=data
        )
        assert response.status_code == 401

    def test_distribution_update(self, client_with_token, orm_product, orm_team):
        contract_id = orm_product.contracts.first().id
        distribution_id = orm_product.contracts.first().distributions.first().id
        data = {"format": "TEST", "type": "F"}
        response = client_with_token([orm_team.scope]).patch(
            f"/products/{orm_product.id}/contracts/{contract_id}/distributions/{distribution_id}",
            data=data,
        )
        assert response.status_code == 200
        assert response.data["format"] == "TEST"

    def test_distribution_update_not_allowed(self, client_with_token, orm_product):
        contract_id = orm_product.contracts.first().id
        distribution_id = orm_product.contracts.first().distributions.first().id
        data = {"format": "TEST", "type": "F"}
        response = client_with_token([]).patch(
            f"/products/{orm_product.id}/contracts/{contract_id}/distributions/{distribution_id}",
            data=data,
        )
        assert response.status_code == 401

    def test_distribution_delete(self, client_with_token, orm_product, orm_team):
        contract_id = orm_product.contracts.first().id
        distribution_id = orm_product.contracts.first().distributions.first().id
        response = client_with_token([orm_team.scope]).delete(
            f"/products/{orm_product.id}/contracts/{contract_id}/distributions/{distribution_id}"
        )
        assert response.status_code == 204

        orm_product.refresh_from_db()
        orm_contract = orm_product.contracts.first()
        assert not orm_contract.distributions.filter(pk=distribution_id).exists()

    def test_distribution_delete_not_allowed(self, client_with_token, orm_product, orm_other_team):
        contract_id = orm_product.contracts.first().id
        distribution_id = orm_product.contracts.first().distributions.first().id
        response = client_with_token([orm_other_team.scope]).delete(
            f"/products/{orm_product.id}/contracts/{contract_id}/distributions/{distribution_id}"
        )
        assert response.status_code == 401

        orm_product.refresh_from_db()
        orm_contract = orm_product.contracts.first()
        assert orm_contract.distributions.filter(pk=distribution_id).exists()

    def test_service_list(self, api_client, orm_product):
        response = api_client.get(f"/products/{orm_product.id}/services")

        assert response.status_code == 200
        assert len(response.data) == 1

    def test_service_create(self, client_with_token, orm_product, orm_team):
        response = client_with_token([orm_team.scope]).post(
            f"/products/{orm_product.id}/services",
            data={"type": "REST", "endpoint_url": "https://api.data.amsterdam.nl/v1/bomen/v2"},
        )
        assert response.status_code == 201

    def test_service_create_empty(self, client_with_token, orm_product, orm_team):
        response = client_with_token([orm_team.scope]).post(
            f"/products/{orm_product.id}/services",
            data={},
        )
        assert response.status_code == 201

    def test_service_update(self, client_with_token, orm_product, orm_team):
        service_id = orm_product.services.first().id
        response = client_with_token([orm_team.scope]).patch(
            f"/products/{orm_product.id}/services/{service_id}", data={"type": "WMS"}
        )
        assert response.status_code == 200

    @pytest.mark.parametrize(
        "data",
        [
            {"type": "API"},  # Wrong type
        ],
    )
    def test_service_update_bad_data(self, client_with_token, data, orm_product, orm_team):
        service_id = orm_product.services.first().id
        response = client_with_token([orm_team.scope]).patch(
            f"/products/{orm_product.id}/services/{service_id}", data=data
        )
        assert response.status_code == 400

    def test_service_delete_not_allowed(self, client_with_token, orm_product, orm_team):
        service_id = orm_product.services.first().id
        response = client_with_token([orm_team.scope]).delete(
            f"/products/{orm_product.id}/services/{service_id}"
        )

        assert response.status_code == 400
        orm_product.refresh_from_db()
        assert len(orm_product.services.all()) == 1

    def test_me_with_scopes(self, client_with_token, orm_product, orm_team, orm_other_team):
        response = client_with_token([orm_team.scope]).get("/me")

        assert response.status_code == 200
        # team
        assert len(response.data["teams"]) == 1
        assert response.data["teams"][0]["name"] == orm_team.name
        assert "acronym" in response.data["teams"][0]
        # product
        assert len(response.data["products"]) == 1
        assert response.data["products"][0]["name"] == orm_product.name
        for key in [
            "team_id",
            "id",
            "type",
            "privacy_level",
            "last_updated",
            "publication_status",
            "contracts",
        ]:
            assert key in response.data["products"][0]
        # contract
        assert len(response.data["products"][0]["contracts"]) == 1
        for key in [
            "id",
            "name",
            "privacy_level",
            "confidentiality",
            "last_updated",
            "publication_status",
        ]:
            assert key in response.data["products"][0]["contracts"][0]

    def test_me_without_scopes(self, client_with_token, orm_product, orm_team, orm_other_team):
        response = client_with_token([]).get("/me")

        assert response.status_code == 200
        assert response.data == {"teams": [], "products": []}
