import pytest

from beheeromgeving.models import DataContract, DataTeam


def test_health(api_client):
    response = api_client.get("/pulse")
    assert response.status_code == 200
    assert response.data == {"status": "OK"}


@pytest.mark.django_db
def test_datateams_list(api_client, datateam):
    response = api_client.get("/datateams")
    assert response.status_code == 200
    assert response.data[0]["acronym"] == "DADI"


@pytest.mark.django_db
def test_datateams_detail(api_client, datateam):
    response = api_client.get(f"/datateams/{datateam.id}")
    assert response.status_code == 200
    assert response.data["acronym"] == "DADI"


@pytest.mark.django_db
def test_datateams_create(api_client):
    response = api_client.post(
        "/datateams",
        data={
            "name": "Basis- en Kernregistratie",
            "acronym": "BENK",
            "product_owner": "Iemand",
            "contact_email": "benk@amsterdam.nl",
        },
    )
    assert response.status_code == 201
    assert response.data["acronym"] == "BENK"


@pytest.mark.django_db
def test_datateams_update(api_client, datateam):
    response = api_client.patch(
        f"/datateams/{datateam.id}",
        data={
            "product_owner": "Iemand Anders",
        },
    )
    assert response.status_code == 200
    assert response.data["product_owner"] == "Iemand Anders"
    assert response.data["acronym"] == "DADI"


@pytest.mark.django_db
def test_datateams_delete(api_client, datateam):
    response = api_client.delete(f"/datateams/{datateam.id}")
    assert response.status_code == 204
    assert DataTeam.objects.count() == 0


@pytest.mark.django_db
def test_datacontracts_list(api_client, datacontract):
    response = api_client.get("/datacontracts")
    assert response.status_code == 200
    assert response.data[0]["name"] == datacontract.name


@pytest.mark.django_db
def test_datacontracts_detail(api_client, datacontract):
    response = api_client.get(f"/datacontracts/{datacontract.name}")
    assert response.status_code == 200
    assert response.data["name"] == "bomen"


@pytest.mark.django_db
def test_datacontracts_create(api_client, datateam):
    response = api_client.post(
        "/datacontracts/",
        data={
            "name": "bommen",
            "description": "bommen in am",
            "purpose": "zodat er niets ontploft",
            "themes": [
                "H",
            ],
            "tags": [],
            "datateam": datateam.id,
            "owner": None,
            "language": "NL",
            "confidentiality": "Openbaar",
            "privacy": "NPI",
            "crs": "WGS84",
            "refresh_period": "3 maanden",
            "retainment_period": 60,
            "start_date": "2025-01-01",
            "schema": None,
            "schema_url": "https://schemas.data.amsterdam.nl/datasets/bommen/dataset",
            "distribution": {
                "id": 1,
                "files": [{"file_format": "csv", "link": "K:\\>file.csv"}],
                "apis": [
                    {"api_type": "REST", "url": "https://api.data.amsterdam.nl/bommen"},
                    {"api_type": "WFS", "url": "https://api.data.amsterdam.nl/bommen/wfs"},
                ],
                "table": True,
            },
            "version": "v1",
        },
    )

    assert response.status_code == 201
    assert response.data["name"] == "bommen"


@pytest.mark.django_db
def test_datacontracts_create_missing_schema(api_client, datateam):
    response = api_client.post(
        "/datacontracts/",
        data={
            "name": "bommen",
            "description": "bommen in am",
            "purpose": "zodat er niets ontploft",
            "themes": [
                "H",
            ],
            "tags": [],
            "datateam": datateam.id,
            "owner": None,
            "language": "NL",
            "confidentiality": "Openbaar",
            "privacy": "NPI",
            "crs": "WGS84",
            "refresh_period": "3 maanden",
            "retainment_period": 60,
            "start_date": "2025-01-01",
            "schema": None,
            "schema_url": None,
            "distribution": {
                "id": 1,
                "files": [{"file_format": "csv", "link": "K:\\>file.csv"}],
                "apis": [
                    {"api_type": "REST", "url": "https://api.data.amsterdam.nl/bommen"},
                    {"api_type": "WFS", "url": "https://api.data.amsterdam.nl/bommen/wfs"},
                ],
                "table": True,
            },
            "version": "v1",
        },
    )

    assert response.status_code == 400
    assert response.data["non_field_errors"][0] == "Either enter a schema, or a schema url."


@pytest.mark.django_db
def test_datacontracts_update(api_client, datacontract):
    response = api_client.patch(
        f"/datacontracts/{datacontract.name}",
        data={
            "owner": "Iemand Anders",
        },
    )
    assert response.status_code == 200
    assert response.data["owner"] == "Iemand Anders"
    assert response.data["name"] == "bomen"


@pytest.mark.django_db
def test_datacontracts_update_crs_sets_is_geo(api_client, datacontract):
    assert datacontract.is_geo
    response = api_client.patch(
        f"/datacontracts/{datacontract.name}",
        data={
            "crs": "NVT",
        },
    )
    assert response.status_code == 200
    datacontract.refresh_from_db()
    assert not datacontract.is_geo


@pytest.mark.django_db
def test_datacontracts_update_schema_and_url_fails(api_client, datacontract):
    response = api_client.patch(
        f"/datacontracts/{datacontract.name}",
        data={
            "schema": {"test": "schema"},
            "schema_url": "https://schemas.data.amsterdam.nl/bomen",
        },
    )
    assert response.status_code == 400
    assert (
        response.data["non_field_errors"][0] == "Either enter a schema, or a schema url, not both."
    )


@pytest.mark.django_db
def test_datacontracts_update_distribution(api_client, datacontract):
    response = api_client.patch(
        f"/datacontracts/{datacontract.name}",
        data={
            "distribution": {
                "table": True,
                "files": [{"file_format": "csv", "link": "K:\\>download.csv"}],
                "apis": [
                    {"api_type": "REST", "url": "https://api.data.amsterdam.nl/bomen"},
                ],
            },
        },
    )
    assert response.status_code == 200
    # should replace the nested fields
    assert len(response.data["distribution"]["apis"]) == 1
    assert response.data["distribution"]["files"][0]["link"].endswith("download.csv")
    assert response.data["name"] == "bomen"


@pytest.mark.django_db
def test_datacontracts_delete(api_client, datacontract):
    response = api_client.delete(f"/datacontracts/{datacontract.name}")
    assert response.status_code == 204
    assert DataContract.objects.count() == 0
