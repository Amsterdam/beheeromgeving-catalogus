import json
from pathlib import Path

import pytest
from rest_framework.test import APIClient

from beheeromgeving.models import DataContract, DataService, Distribution, Product, Team
from tests.utils import build_jwt_token


@pytest.fixture()
def api_client() -> APIClient:
    """Return a client that has unhindered access to the API views"""
    api_client = APIClient()
    api_client.default_format = "json"  # instead of multipart
    return api_client


@pytest.fixture()
def orm_team() -> Team:
    return Team.objects.create(
        name="DataDiensten",
        acronym="DADI",
        description="",
        po_name="Someone",
        po_email="someone.dadi@amsterdam.nl",
        contact_email="dadi@amsterdam.nl",
        scope="scope_dadi",
    )


@pytest.fixture()
def orm_other_team() -> Team:
    return Team.objects.create(
        name="Beheer Openbare Ruimte",
        acronym="BOR",
        description="",
        po_name="Jan Bor",
        po_email="j.bor@amsterdam.nl",
        contact_email="bor@amsterdam.nl",
        scope="scope_bor",
    )


@pytest.fixture()
def orm_product(orm_team) -> Product:
    product = Product.objects.create(
        name="bomen",
        description="bomen in Amsterdam",
        team=orm_team,
        data_steward="meneerboom@amsterdam.nl",
        language="NL",
        is_geo=True,
        schema_url="https://schemas.data.amsterdam.nl/datasets/bomen/dataset",
        type="D",
        themes=["NM"],
        privacy_level="NPI",
        refresh_period={"frequency": 3, "unit": "MONTH"},
        publication_status="D",
    )

    service = DataService.objects.create(
        product=product, type="REST", endpoint_url="https://api.data.amsterdam.nl/v1/bomen"
    )

    contract = DataContract.objects.create(
        product=product,
        publication_status="D",
        purpose="onderhoud van bomen",
        name="beheer bomen",
        description="contract voor data nodig voor het beheer van bomen",
        privacy_level="NPI",
        scope="scope_bomen_beheer",
        confidentiality="I",
        start_date="2025-01-01",
        retainment_period=12,
    )

    Distribution.objects.create(
        contract=contract,
        access_service=service,
        type="A",
    )
    Distribution.objects.create(
        contract=contract,
        download_url="https://bomen.amsterdam.nl/beheer.csv",
        format="csv",
        type="F",
    )

    return product


@pytest.fixture()
def client_with_token(api_client):
    class Client:
        def __init__(self, scopes: list[str] | None = None):
            self._token = build_jwt_token(scopes or [])
            self.kwargs = {"HTTP_AUTHORIZATION": f"Bearer {self._token}"}

        def get(self, route):
            return api_client.get(route, **self.kwargs)

        def patch(self, route, data):
            return api_client.patch(route, data, **self.kwargs)

        def post(self, route, data):
            return api_client.post(route, data, **self.kwargs)

        def delete(self, route):
            return api_client.delete(route, **self.kwargs)

    return Client


@pytest.fixture()
def product_json():
    with open(Path(__file__).parent / "product.json") as file:
        return json.load(file)
