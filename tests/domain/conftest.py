from datetime import datetime

import pytest

from domain.auth import AuthorizationService, authorize
from domain.product import (
    DataContract,
    DataService,
    Distribution,
    Product,
    ProductService,
    RefreshPeriod,
    enums,
)
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
    assert team.id
    return Product(
        id=1,
        name="bomen",
        description="bomen in Amsterdam",
        team_id=team.id,
        contact_email=team.contact_email,
        language=enums.Language.NEDERLANDS,
        is_geo=True,
        crs=enums.CoordRefSystem.RD,
        schema_url="https://schemas.data.amsterdam.nl/datasets/bomen/dataset",
        type=enums.ProductType.DATAPRODUCT,
        themes=[enums.Theme.NATUUR_EN_MILIEU],
        data_steward="meneerboom@amsterdam.nl",
        refresh_period=RefreshPeriod.from_dict({"frequency": 3, "unit": "MONTH"}),
        last_updated=datetime.fromisoformat("2025-09-04T11:25:05+00"),
        created_at=datetime.fromisoformat("2025-09-04T10:25:05+00"),
        publication_status=enums.PublicationStatus.DRAFT,
        services=[
            DataService(
                id=1,
                type=enums.DataServiceType.REST,
                endpoint_url="https://api.data.amsterdam.nl/v1/bomen",
            )
        ],
        contracts=[
            DataContract(
                id=1,
                publication_status=enums.PublicationStatus.DRAFT,
                purpose="onderhoud van bomen",
                name="beheer bomen",
                description="contract voor data nodig voor het beheer van bomen",
                privacy_level=enums.PrivacyLevel.NIET_PERSOONLIJK_IDENTIFICEERBAAR,
                scopes=["bomen_beheer"],
                confidentiality=enums.ConfidentialityLevel.INTERN,
                start_date=datetime.fromisoformat("2025-01-01T00:00:00+00"),
                retainment_period=12,
                distributions=[
                    Distribution(
                        id=1,
                        access_service_id=1,
                        type=enums.DistributionType.API,
                    ),
                    Distribution(
                        id=2,
                        download_url="https://bomen.amsterdam.nl/beheer.csv",
                        format="csv",
                        type=enums.DistributionType.FILE,
                        filename="beheer.csv",
                    ),
                ],
            )
        ],
    )


@pytest.fixture()
def auth_repo(team, other_team, product) -> DummyAuthRepo:
    return DummyAuthRepo(teams=[team, other_team], products=[product])


@pytest.fixture()
def auth_service(auth_repo) -> AuthorizationService:
    return AuthorizationService(auth_repo)


@pytest.fixture()
def init_auth(auth_service) -> None:
    authorize.set_auth_service(auth_service)


@pytest.fixture()
def team_service(team, init_auth, auth_repo) -> TeamService:
    repo = DummyRepository(objects=[team], auth_repo=auth_repo)
    return TeamService(repo)


@pytest.fixture()
def product_service(product, init_auth, auth_repo) -> ProductService:
    return ProductService(repo=DummyRepository([product], auth_repo=auth_repo))
