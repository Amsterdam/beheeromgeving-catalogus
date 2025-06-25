from __future__ import annotations

from pathlib import Path

import pytest
from rest_framework.test import APIClient

from beheeromgeving.models import (
    APIDistribution,
    DataContract,
    DataTeam,
    Distribution,
    FileDistribution,
)

HERE = Path(__file__).parent


@pytest.fixture()
def api_client() -> APIClient:
    """Return a client that has unhindered access to the API views"""
    api_client = APIClient()
    api_client.default_format = "json"  # instead of multipart
    return api_client


@pytest.fixture()
def datateam() -> DataTeam:
    return DataTeam.objects.create(
        name="DataDiensten",
        acronym="DADI",
        product_owner="Someone",
        contact_email="dadi@amsterdam.nl",
    )


@pytest.fixture()
def datacontract(datateam) -> DataContract:
    distribution = Distribution.objects.create(table=True)
    FileDistribution.objects.create(
        file_format="csv", link=r"K:\>file.csv", distribution=distribution
    )
    APIDistribution.objects.create(
        api_type="REST", url="https://api.data.amsterdam.nl/bomen", distribution=distribution
    )
    APIDistribution.objects.create(
        api_type="WFS", url="https://api.data.amsterdam.nl/bomen/wfs", distribution=distribution
    )
    return DataContract.objects.create(
        name="bomen",
        description="bomen in Amsterdam",
        purpose="onderhoud van bomen",
        themes=["NM"],
        tags=["bomen", "groen"],
        datateam=datateam,
        language="NL",
        confidentiality="Openbaar",
        privacy="NPI",
        is_geo=True,
        crs="WGS84",
        refresh_period="3 maanden",
        retainment_period=1200,
        start_date="2025-01-01",
        schema_url="https://schemas.data.amsterdam.nl/datasets/bomen/dataset",
        version="v1",
        distribution=distribution,
    )
