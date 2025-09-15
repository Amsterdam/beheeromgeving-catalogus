from datetime import datetime

import pytest

from domain.auth import AuthorizationService, authorize
from domain.product import DataContract, DataService, Distribution, Product, ProductService
from domain.team import Team, TeamService
from tests.domain.utils import DummyAuthRepo, DummyRepository


@pytest.fixture()
def team() -> Team:
    return Team(
        id=1,
        name="DataDiensten",
        acronym="DADI",
        description="",
        po_name="Someone",
        po_email="someone.dadi@amsterdam.nl",
        contact_email="dadi@amsterdam.nl",
        scope="scope_dadi",
    )


@pytest.fixture()
def other_team() -> Team:
    return Team(
        id=2,
        name="Beheer Openbare Ruimte",
        acronym="BOR",
        description="",
        po_name="Jan Bor",
        po_email="j.bor@amsterdam.nl",
        contact_email="bor@amsterdam.nl",
        scope="scope_bor",
    )


@pytest.fixture()
def product(team: Team) -> Product:
    return Product(
        id=1,
        name="bomen",
        description="bomen in Amsterdam",
        team_id=team.id,
        language="NL",
        is_geo=True,
        schema_url="https://schemas.data.amsterdam.nl/datasets/bomen/dataset",
        type="D",
        themes=["NM"],
        tags=["bomen", "groen"],
        has_personal_data=False,
        has_special_personal_data=False,
        refresh_period="3 maanden",
        last_updated=datetime.fromisoformat("2025-09-04T11:25:05+00"),
        publication_status="D",
        services=[
            DataService(id=1, type="REST", endpoint_url="https://api.data.amsterdam.nl/v1/bomen")
        ],
        contracts=[
            DataContract(
                id=1,
                publication_status="D",
                purpose="onderhoud van bomen",
                conditions="voorwaarden: ja",
                name="beheer bomen",
                description="contract voor data nodig voor het beheer van bomen",
                data_steward="meneerboom@amsterdam.nl",
                has_personal_data=False,
                has_special_personal_data=False,
                profile="scope_bomen_beheer",
                confidentiality="I",
                start_date="2025-01-01",
                retainment_period=12,
                distributions=[
                    Distribution(
                        access_service_id=1,
                        type="A",
                    ),
                    Distribution(
                        download_url="https://bomen.amsterdam.nl/beheer.csv",
                        format="csv",
                        type="F",
                    ),
                ],
            )
        ],
    )


@pytest.fixture()
def init_auth(team, other_team, product) -> None:
    auth_service = AuthorizationService(
        DummyAuthRepo(teams=[team, other_team], products=[product])
    )
    authorize.set_auth_service(auth_service)


@pytest.fixture()
def team_service(team, init_auth) -> TeamService:
    repo = DummyRepository(objects=[team])
    return TeamService(repo)


@pytest.fixture()
def product_service(product, init_auth) -> ProductService:
    return ProductService(repo=DummyRepository([product]))
