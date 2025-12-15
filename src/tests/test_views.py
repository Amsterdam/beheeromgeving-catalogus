"""
Tests for the views.

NB: Since the services are instantiated outside the viewsets, they will need to be
refreshed if objects are created or altered outside the regular flow (i.e. directly through the
django ORM models). This is done in the api_client fixture, so any time a orm_* fixture is used,
the api_client or client_with_token fixtures need to be the last one.
"""

import pytest
from django.conf import settings
from pytest_django.asserts import assertNumQueries

from beheeromgeving.models import Product, Team


@pytest.mark.django_db
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

    def test_teams_list(self, orm_team, api_client):
        response = api_client.get("/teams")
        assert response.status_code == 200
        assert response.data[0]["acronym"] == "DADI"

    def test_teams_detail(self, orm_team, api_client):
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

    def test_teams_update(self, orm_team, client_with_token):
        response = client_with_token([settings.ADMIN_ROLE_NAME]).patch(
            f"/teams/{orm_team.id}",
            data={
                "po_name": "Iemand Anders",
            },
        )
        assert response.status_code == 200

        orm_team.refresh_from_db()
        assert orm_team.po_name == "Iemand Anders"

    def test_teams_delete_by_admin(self, orm_team, client_with_token):
        response = client_with_token([settings.ADMIN_ROLE_NAME]).delete(f"/teams/{orm_team.id}")
        assert response.status_code == 204
        assert Team.objects.count() == 0

    def test_teams_delete_unauthorized(self, orm_team, client_with_token):
        response = client_with_token(["some_unauthorized_scope"]).delete(f"/teams/{orm_team.id}")
        assert response.status_code == 401
        assert Team.objects.count() == 1

    def test_products_list(self, orm_product, api_client):
        response = api_client.get("/products")
        assert response.status_code == 200
        product = response.data["results"][0]
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

    @pytest.mark.parametrize(
        "query_string,expected",
        [
            ("", ("http://testserver/products?page=2", None, 10)),
            ("?page=2", ("http://testserver/products?page=3", "http://testserver/products", 10)),
            ("?page=3", (None, "http://testserver/products?page=2", 6)),
            ("?pagesize=13", ("http://testserver/products?page=2&pagesize=13", None, 13)),
            ("?pagesize=13&page=2", (None, "http://testserver/products?pagesize=13", 13)),
            ("?pagesize=50", (None, None, 26)),
        ],
    )
    def test_products_list_pagination(self, many_orm_products, api_client, query_string, expected):
        response = api_client.get(f"/products{query_string}")
        assert response.status_code == 200
        assert response.data["count"] == 26
        assert response.data["next"] == expected[0]
        assert response.data["previous"] == expected[1]
        assert len(response.data["results"]) == expected[2]

    def test_products_list_pagination_invalid_page(self, many_orm_products, api_client):
        response = api_client.get("/products?page=5")
        assert response.status_code == 404
        assert response.data == "Page not found: 5. Page must be between 1 and 3 (inclusive)."

    def test_products_list_omits_non_published_by_default(
        self, many_orm_products, non_published_products, api_client
    ):
        response = api_client.get("/products")
        assert response.status_code == 200
        assert response.data["count"] == 26

    def test_products_list_cannot_filter_on_publication_status(
        self, many_orm_products, non_published_products, api_client
    ):
        response = api_client.get("/products?publication_status=D")
        assert response.status_code == 200
        assert response.data["count"] == 26  # still only published products

    def test_product_endpoint_queries_db_sparingly(self, orm_product, orm_team, client_with_token):
        """Assert that the db is not hit repeatedly for consecutive requests.

        i.e. Products are cached in the repository."""
        api_client = client_with_token([orm_team.scope])
        # warm up the cache in the client:
        response = api_client.get("/products")
        assert response.status_code == 200

        # subsequent requests should hit the cache
        with assertNumQueries(0):
            response = api_client.get("/products")
            assert response.status_code == 200

            response = api_client.get(f"/products/{orm_product.id}")
            assert response.status_code == 200

            response = api_client.get(f"/products/{orm_product.id}/contracts")
            assert response.status_code == 200

            response = api_client.get(f"/products/{orm_product.id}/services")
            assert response.status_code == 200

            response = api_client.get(f"/products?name={orm_product.name}/services")
            assert response.status_code == 200

    def test_product_list_query_by_name(self, orm_product, api_client):
        """Assert we can query the products based on name.

        This name can be snakecased with a version suffix."""
        response = api_client.get("/products?name=bomen_v1")
        assert response.status_code == 200
        product = response.data
        assert product["name"] == orm_product.name
        # check a property that is only in detail view, as this should return a ProductDetail.
        assert product["privacy_level"] == orm_product.privacy_level

    def test_product_list_query_by_name_404(self, api_client, orm_product):
        """Assert query by name returns 404 when we cannot find the product."""
        response = api_client.get("/products?name=fietspaaltjes_v1")
        assert response.status_code == 404
        assert response.data == "Product with name fietspaaltjes_v1 does not exist."

    def test_product_list_query_matches_product_name(self, orm_product, orm_product2, api_client):
        """Assert that we can query the products on product name."""
        response = api_client.get("/products?q=fietspaaltjes")
        assert response.status_code == 200
        # only product2 is returned
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["name"] == orm_product2.name

    def test_product_list_query_and_filter_matches(self, orm_product, orm_product2, api_client):
        """Assert that we can query and filter products."""
        response = api_client.get(f"/products?q=fietspaaltjes&team={orm_product2.team.id}")
        assert response.status_code == 200
        # only product2 is returned
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["name"] == orm_product2.name

    def test_product_list_query_and_filter_do_not_match(
        self, orm_product, orm_product2, api_client
    ):
        """Assert that no products return when there are no query and filter matches."""
        response = api_client.get(f"/products?q=fietspaaltjes&team={orm_product.team.id}")
        assert response.status_code == 200
        # no product is returned
        assert len(response.data["results"]) == 0

    def test_product_list_filter_matches_team_name(self, orm_product, orm_product2, api_client):
        """Assert that we can filter the products on team id."""
        response = api_client.get(f"/products?team={orm_product.team.id}")
        assert response.status_code == 200

        # only product1 is returned
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["team_id"] == orm_product.team.id

    def test_product_list_filter_matches_theme(self, orm_product, orm_product2, api_client):
        """Assert that we can filter the products on theme."""
        response = api_client.get("/products?theme=MI")
        assert response.status_code == 200
        # only product2 is returned
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["themes"] == orm_product2.themes

    def test_product_list_filter_matches_themes(self, orm_product, orm_product2, api_client):
        """Assert that we can filter the products on multiple themes."""
        response = api_client.get("/products?theme=NM,MI")
        assert response.status_code == 200
        # both products are returned
        assert len(response.data["results"]) == 2
        assert response.data["results"][0]["themes"] == orm_product.themes
        assert response.data["results"][1]["themes"] == orm_product2.themes

    def test_contract_list_filter_matches_confidentiality(
        self, orm_product, orm_product2, api_client
    ):
        """Assert that we can filter the contracts on confidentiality."""
        response = api_client.get("/products?confidentiality=I")
        assert response.status_code == 200
        # only product1 is returned
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["name"] == orm_product.name

    def test_product_list_filter_matches_type(self, orm_product, orm_product2, api_client):
        """Assert that we can filter the products on distribution type."""
        response = api_client.get("/products?type=F")
        assert response.status_code == 200
        # only product1 is returned
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["name"] == orm_product.name

    def test_product_list_filter_matches_type_multiple(
        self, orm_product, orm_product2, api_client
    ):
        """Assert that we can filter the products on distribution type."""
        response = api_client.get("/products?type=F,A")
        assert response.status_code == 200
        # both products are returned
        assert len(response.data["results"]) == 2

    def test_product_list_filter_matches_language(self, orm_product, orm_product2, api_client):
        """Assert that we can filter the products on distribution type."""
        response = api_client.get("/products?language=NL")
        assert response.status_code == 200
        # only product1 is returned
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["name"] == orm_product.name

    @pytest.mark.parametrize(
        "order,expected_name",
        [
            ("-name", "naam z"),
            ("name", "naam a"),
            ("last_updated", "naam m"),  # m has the earliest update date
            ("-last_updated", "naam n"),  # n has the lastest update date
            ("created_at", "naam m"),  # m has the earliest creation date
            ("-created_at", "naam n"),  # n has the latest creation date
        ],
    )
    def test_product_list_order(self, many_orm_products, api_client, order, expected_name):
        response = api_client.get(f"/products?order={order}")
        assert response.status_code == 200
        assert response.data["results"][0]["name"] == expected_name

    def test_product_list_filter_matches_multiple_filter_params(
        self, orm_product, orm_product2, api_client
    ):
        """Assert that we can filter on multiple parameters in no particular order."""
        response = api_client.get(f"/products?confidentiality=I&team={orm_product.team.id}&type=F")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["name"] == orm_product.name

    def test_product_list_no_filter_matches(self, orm_product, orm_product2, api_client):
        """Return status code 200 if no results return when filtered on."""
        response = api_client.get(f"/products?confidentiality=I&team={orm_product.team.id}&type=A")

        assert response.status_code == 200

    def test_product_list_non_existing_team_filter(self, orm_product, orm_product2, api_client):
        """Assert filter by team id returns empty results when we cannot find the team."""
        response = api_client.get("/products?team=0")

        assert response.status_code == 200
        assert len(response.data["results"]) == 0

    def test_product_list_query_matches_product_description(
        self, orm_product, orm_product2, api_client
    ):
        """Assert that we can query the products on product description."""
        response = api_client.get("/products?q=weg")
        assert response.status_code == 200
        # only product2 is returned
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["name"] == orm_product2.name

    def test_product_list_query_matches_contract_name(self, orm_product, orm_product2, api_client):
        """Assert that we can query the products on contract name."""
        response = api_client.get("/products?q=fietspaaltjes")
        assert response.status_code == 200
        # only product2 is returned
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["name"] == orm_product2.name

    def test_product_list_query_matches_contract_description(
        self, orm_product, orm_product2, api_client
    ):
        """Assert that we can query the products on contract description."""
        response = api_client.get("/products?q=fietspaden")
        assert response.status_code == 200
        # only product2 is returned
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["name"] == orm_product2.name

    def test_product_list_query_matches_some_words(self, orm_product, orm_product2, api_client):
        """Assert that a query matches on one or more words rather than all words."""
        response = api_client.get("/products?q=fietspaaltjes bomen")
        assert response.status_code == 200
        # both are returned
        assert len(response.data["results"]) == 2

    def test_product_list_query_orders_by_no_of_occurences(
        self, orm_product, orm_product2, api_client
    ):
        """Assert that the query result is ordered by number of occurences."""
        response = api_client.get("/products?q=fietspaaltjes fietspaden bomen")
        assert response.status_code == 200
        # both are returned
        assert len(response.data["results"]) == 2
        assert (
            response.data["results"][0]["id"] == orm_product2.id
        )  # fietspaaltjes, fietspaden; count: 2
        assert response.data["results"][1]["id"] == orm_product.id  # bomen; count: 1

    def test_product_detail(self, orm_product, api_client):
        response = api_client.get(f"/products/{orm_product.id}")
        assert response.status_code == 200
        assert response.data["name"] == orm_product.name
        assert response.data["missing_fields"] == []

    def test_product_detail_missing_fields(self, orm_incomplete_product, api_client):
        response = api_client.get(f"/products/{orm_incomplete_product.id}")
        assert response.status_code == 200
        assert response.data["name"] == orm_incomplete_product.name
        assert response.data["missing_fields"] == ["crs", "privacy_level"]

    def test_product_create(self, orm_team, client_with_token):
        response = client_with_token([orm_team.scope]).post(
            "/products",
            data={"type": "D", "team_id": orm_team.id},
        )
        assert response.status_code == 201

    def test_product_delete(self, orm_team, orm_product, client_with_token):
        response = client_with_token([orm_team.scope]).delete(f"/products/{orm_product.id}")
        assert response.status_code == 204
        with pytest.raises(Product.DoesNotExist):
            orm_product.refresh_from_db()

    def test_product_delete_unauthorized(self, orm_product, client_with_token):
        response = client_with_token([]).delete(f"/products/{orm_product.id}")
        assert response.status_code == 401

    @pytest.mark.parametrize(
        "data",
        [
            {"refresh_period": 2},  # Wrong type
        ],
    )
    def test_product_create_bad_data(self, data, orm_team, client_with_token):
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
    def test_product_update(self, orm_product, orm_team, data, client_with_token):
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

    def test_product_update_refresh_period(self, orm_product, orm_team, client_with_token):
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
    def test_set_state_product(self, orm_product, orm_team, data, client_with_token):
        response = client_with_token([orm_team.scope]).post(
            f"/products/{orm_product.id}/set-state",
            data=data,
        )
        assert response.status_code == 200
        orm_product.refresh_from_db()

        assert orm_product.publication_status == data["publication_status"]
        assert response.data["publication_status"] == orm_product.publication_status

    @pytest.mark.parametrize(
        "data",
        [
            {"publication_status": "D"},
            {"publication_status": "P"},
        ],
    )
    def test_set_state_contract(self, orm_product, orm_team, data, client_with_token):
        contract_id = orm_product.contracts.first().id
        response = client_with_token([orm_team.scope]).post(
            f"/products/{orm_product.id}/contracts/{contract_id}/set-state", data=data
        )
        assert response.status_code == 200
        orm_product.refresh_from_db()

        assert orm_product.contracts.first().publication_status == data["publication_status"]
        assert (
            response.data["publication_status"] == orm_product.contracts.first().publication_status
        )

    def test_contract_list(self, orm_product, api_client):
        response = api_client.get(f"/products/{orm_product.id}/contracts")

        assert response.status_code == 200
        assert len(response.data) == 1

    def test_contract_detail(self, orm_product, api_client):
        contract_id = orm_product.contracts.first().id
        response = api_client.get(f"/products/{orm_product.id}/contracts/{contract_id}")

        assert response.status_code == 200
        assert response.data["name"] == orm_product.contracts.first().name
        assert response.data["missing_fields"] == []

    def test_contract_detail_missing_fields(self, orm_incomplete_product, api_client):
        contract_id = orm_incomplete_product.contracts.first().id
        response = api_client.get(f"/products/{orm_incomplete_product.id}/contracts/{contract_id}")

        assert response.status_code == 200
        assert response.data["name"] == orm_incomplete_product.contracts.first().name
        assert response.data["missing_fields"] == ["confidentiality"]

    def test_contract_create(self, orm_product, orm_team, client_with_token):
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
    def test_contract_update(self, orm_product, orm_team, data, client_with_token):
        contract_id = orm_product.contracts.first().id
        response = client_with_token([orm_team.scope]).patch(
            f"/products/{orm_product.id}/contracts/{contract_id}", data=data
        )
        print(response.data)
        assert response.status_code == 200

    @pytest.mark.parametrize(
        "data",
        [
            {"name": 2},  # Wrong type
            {"distributions": [{"type": 3}]},  # Wrong type on subfield
        ],
    )
    def test_contract_update_bad_data(self, data, orm_product, orm_team, client_with_token):
        contract_id = orm_product.contracts.first().id
        response = client_with_token([orm_team.scope]).patch(
            f"/products/{orm_product.id}/contracts/{contract_id}", data=data
        )
        assert response.status_code == 400

    def test_contract_delete(self, orm_product, orm_team, client_with_token):
        contract_id = orm_product.contracts.first().id
        response = client_with_token([orm_team.scope]).delete(
            f"/products/{orm_product.id}/contracts/{contract_id}"
        )

        assert response.status_code == 204
        orm_product.refresh_from_db()

        assert len(orm_product.contracts.all()) == 0

    def test_distribution_list(self, orm_product, api_client):
        contract_id = orm_product.contracts.first().id
        response = api_client.get(
            f"/products/{orm_product.id}/contracts/{contract_id}/distributions"
        )
        assert response.status_code == 200
        assert len(response.data) == 2

    def test_distribution_detail(self, orm_product, api_client):
        contract_id = orm_product.contracts.first().id
        distribution_id = orm_product.contracts.first().distributions.first().id
        response = api_client.get(
            f"/products/{orm_product.id}/contracts/{contract_id}/distributions/{distribution_id}"
        )
        assert response.status_code == 200
        assert response.data["type"] == "A"  # API

    def test_distribution_detail_404(self, orm_product, api_client):
        contract_id = orm_product.contracts.first().id
        response = api_client.get(
            f"/products/{orm_product.id}/contracts/{contract_id}/distributions/1337"
        )
        assert response.status_code == 404

    def test_distribution_create(self, orm_product, orm_team, client_with_token):
        contract_id = orm_product.contracts.first().id
        data = {"format": "TEST", "type": "F"}
        response = client_with_token([orm_team.scope]).post(
            f"/products/{orm_product.id}/contracts/{contract_id}/distributions", data=data
        )
        assert response.status_code == 201

    def test_distribution_create_empty(self, orm_product, orm_team, client_with_token):
        contract_id = orm_product.contracts.first().id
        data = {}
        response = client_with_token([orm_team.scope]).post(
            f"/products/{orm_product.id}/contracts/{contract_id}/distributions", data=data
        )
        assert response.status_code == 201

    def test_distribution_create_not_allowed(self, orm_product, orm_other_team, client_with_token):
        contract_id = orm_product.contracts.first().id
        data = {"format": "TEST", "type": "F"}
        response = client_with_token([orm_other_team.scope]).post(
            f"/products/{orm_product.id}/contracts/{contract_id}/distributions", data=data
        )
        assert response.status_code == 401

    def test_distribution_update(self, orm_product, orm_team, client_with_token):
        contract_id = orm_product.contracts.first().id
        distribution_id = orm_product.contracts.first().distributions.first().id
        data = {"format": "TEST", "type": "F"}
        response = client_with_token([orm_team.scope]).patch(
            f"/products/{orm_product.id}/contracts/{contract_id}/distributions/{distribution_id}",
            data=data,
        )
        assert response.status_code == 200
        assert response.data["format"] == "TEST"

    def test_distribution_patch_and_then_get(self, orm_product, orm_team, client_with_token):
        contract_id = orm_product.contracts.first().id
        distribution_id = orm_product.contracts.first().distributions.first().id
        data = {
            "format": "TEST",
            "type": "F",
            "filename": "test.csv",
            "refresh_period": {"frequency": 3, "unit": "DAY"},
        }
        url = f"/products/{orm_product.id}/contracts/{contract_id}/distributions/{distribution_id}"
        client_with_token([orm_team.scope]).patch(
            url,
            data=data,
        )
        response = client_with_token([]).get(url)
        assert response.status_code == 200
        for k, v in data.items():
            assert response.data[k] == v

    def test_distribution_update_not_allowed(self, orm_product, client_with_token):
        contract_id = orm_product.contracts.first().id
        distribution_id = orm_product.contracts.first().distributions.first().id
        data = {"format": "TEST", "type": "F"}
        response = client_with_token([]).patch(
            f"/products/{orm_product.id}/contracts/{contract_id}/distributions/{distribution_id}",
            data=data,
        )
        assert response.status_code == 401

    def test_distribution_delete(self, orm_product, orm_team, client_with_token):
        contract_id = orm_product.contracts.first().id
        distribution_id = orm_product.contracts.first().distributions.first().id
        response = client_with_token([orm_team.scope]).delete(
            f"/products/{orm_product.id}/contracts/{contract_id}/distributions/{distribution_id}"
        )
        assert response.status_code == 204

        orm_product.refresh_from_db()
        orm_contract = orm_product.contracts.first()
        assert not orm_contract.distributions.filter(pk=distribution_id).exists()

    def test_distribution_delete_not_allowed(self, orm_product, orm_other_team, client_with_token):
        contract_id = orm_product.contracts.first().id
        distribution_id = orm_product.contracts.first().distributions.first().id
        response = client_with_token([orm_other_team.scope]).delete(
            f"/products/{orm_product.id}/contracts/{contract_id}/distributions/{distribution_id}"
        )
        assert response.status_code == 401

        orm_product.refresh_from_db()
        orm_contract = orm_product.contracts.first()
        assert orm_contract.distributions.filter(pk=distribution_id).exists()

    def test_service_list(self, orm_product, api_client):
        response = api_client.get(f"/products/{orm_product.id}/services")

        assert response.status_code == 200
        assert len(response.data) == 1

    def test_service_detail(self, orm_product, api_client):
        response = api_client.get(
            f"/products/{orm_product.id}/services/{orm_product.services.first().id}"
        )

        assert response.status_code == 200
        assert response.data["id"] == orm_product.services.first().id

    def test_service_create(self, orm_product, orm_team, client_with_token):
        response = client_with_token([orm_team.scope]).post(
            f"/products/{orm_product.id}/services",
            data={"type": "REST", "endpoint_url": "https://api.data.amsterdam.nl/v1/bomen/v2"},
        )
        assert response.status_code == 201

    def test_service_create_empty(self, orm_product, orm_team, client_with_token):
        response = client_with_token([orm_team.scope]).post(
            f"/products/{orm_product.id}/services",
            data={},
        )
        assert response.status_code == 201

    def test_service_update(self, orm_product, orm_team, client_with_token):
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
    def test_service_update_bad_data(self, data, orm_product, orm_team, client_with_token):
        service_id = orm_product.services.first().id
        response = client_with_token([orm_team.scope]).patch(
            f"/products/{orm_product.id}/services/{service_id}", data=data
        )
        assert response.status_code == 400

    def test_service_delete(self, orm_product, orm_team, client_with_token):
        # first delete the distribution referencing the service:
        contract = orm_product.contracts.first()
        distribution_id = contract.distributions.first().id
        client_with_token([orm_team.scope]).delete(
            f"/products/{orm_product.id}/contracts/{contract.id}/distributions/{distribution_id}"
        )
        # delete the service:
        service_id = orm_product.services.first().id
        response = client_with_token([orm_team.scope]).delete(
            f"/products/{orm_product.id}/services/{service_id}"
        )

        assert response.status_code == 204
        orm_product.refresh_from_db()
        assert len(orm_product.services.all()) == 0

    def test_service_delete_not_allowed(self, orm_product, orm_team, client_with_token):
        service_id = orm_product.services.first().id
        response = client_with_token([orm_team.scope]).delete(
            f"/products/{orm_product.id}/services/{service_id}"
        )

        assert response.status_code == 400
        orm_product.refresh_from_db()
        assert len(orm_product.services.all()) == 1

    def test_me_with_scopes(self, orm_product, orm_team, orm_other_team, client_with_token):
        response = client_with_token([orm_team.scope]).get("/me")

        assert response.status_code == 200
        # team
        assert len(response.data["teams"]) == 1
        assert response.data["teams"][0]["name"] == orm_team.name
        assert "acronym" in response.data["teams"][0]
        # product
        assert len(response.data["products"]["results"]) == 1
        assert response.data["products"]["results"][0]["name"] == orm_product.name
        for key in [
            "team_id",
            "id",
            "type",
            "privacy_level",
            "last_updated",
            "publication_status",
            "contracts",
        ]:
            assert key in response.data["products"]["results"][0]
        # contract
        assert len(response.data["products"]["results"][0]["contracts"]) == 1
        for key in [
            "id",
            "name",
            "privacy_level",
            "confidentiality",
            "last_updated",
            "publication_status",
        ]:
            assert key in response.data["products"]["results"][0]["contracts"][0]

    @pytest.mark.parametrize(
        "query_string,expected",
        [
            ("", ("http://testserver/me?page=2", None, 10)),
            ("?page=2", ("http://testserver/me?page=3", "http://testserver/me", 10)),
            ("?pagesize=50", (None, None, 26)),
            ("?page=2&pagesize=20", (None, "http://testserver/me?pagesize=20", 6)),
        ],
    )
    def test_me_pagination(
        self, many_orm_products, orm_team, client_with_token, query_string, expected
    ):
        response = client_with_token([orm_team.scope]).get(f"/me{query_string}")

        assert response.status_code == 200
        products = response.data["products"]
        assert products["next"] == expected[0]
        assert products["previous"] == expected[1]
        assert len(products["results"]) == expected[2]

    def test_me_pagination_invalid_page(self, many_orm_products, orm_team, client_with_token):
        response = client_with_token([orm_team.scope]).get("/me?page=5")

        assert response.status_code == 404
        assert response.data == "Page not found: 5. Page must be between 1 and 3 (inclusive)."

    def test_me_without_scopes(self, orm_product, orm_team, orm_other_team, client_with_token):
        response = client_with_token([]).get("/me")

        assert response.status_code == 200
        assert response.data == {
            "teams": [],
            "products": {"count": 0, "next": None, "previous": None, "results": []},
        }

    def test_me_default_product_order(self, many_orm_products, orm_team, client_with_token):
        response = client_with_token([orm_team.scope]).get("/me")
        assert response.status_code == 200
        products = response.data["products"]["results"]
        assert products[0]["last_updated"] > products[1]["last_updated"]

    def test_me_custom_product_order(self, many_orm_products, orm_team, client_with_token):
        response = client_with_token([orm_team.scope]).get("/me?order=name")
        assert response.status_code == 200
        products = response.data["products"]["results"]
        assert products[0]["name"] == "naam a"

    def test_me_bad_request(self, many_orm_products, orm_team, client_with_token):
        response = client_with_token([orm_team.scope]).get("/me?language=FR")
        assert response.status_code == 400
        assert "Input should be 'NL' or 'EN'" in response.data

    def test_me_includes_unpublished_products_by_default(
        self, many_orm_products, non_published_products, orm_team, client_with_token
    ):
        response = client_with_token([orm_team.scope]).get("/me")
        assert response.status_code == 200
        assert response.data["products"]["count"] == 30

    def test_me_can_filter_on_publication_status(
        self, many_orm_products, non_published_products, orm_team, client_with_token
    ):
        response = client_with_token([orm_team.scope]).get("/me?publication_status=D")
        assert response.status_code == 200
        assert response.data["products"]["count"] == 1
