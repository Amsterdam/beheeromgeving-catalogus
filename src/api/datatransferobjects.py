from collections.abc import Sequence
from datetime import date, datetime
from typing import Literal, overload

from django.db.models.manager import BaseManager
from pydantic import BaseModel, ConfigDict, Field, field_validator

from domain.product import enums, objects
from domain.team import Team as DomainTeam


@overload
def to_response_object(obj: Sequence[objects.BaseObject], dto_type: str) -> list[dict]: ...


@overload
def to_response_object(obj: objects.BaseObject, dto_type: str) -> dict: ...


def to_response_object(
    obj: objects.BaseObject | Sequence[objects.BaseObject], dto_type: str | None = None
) -> dict | list[dict]:
    if isinstance(obj, Sequence):
        return [to_dto(el, dto_type=dto_type or "list").model_dump() for el in obj]
    return to_dto(obj, dto_type=dto_type or "detail").model_dump()


def to_dto(domain_object: objects.BaseObject, dto_type: str = "detail") -> BaseModel:
    OBJECT_MAPPING: dict[type[objects.BaseObject], dict[str, type[BaseModel]]] = {
        DomainTeam: {
            "detail": Team,
            "list": TeamList,
            "me": TeamList,
        },
        objects.DataContract: {
            "detail": DataContract,
            "list": DataContractList,
        },
        objects.Product: {
            "detail": ProductDetail,
            "list": ProductList,
            "me": MyProduct,
        },
        objects.DataService: {
            "detail": DataService,
            "list": DataService,
        },
        objects.Distribution: {
            "detail": Distribution,
            "list": Distribution,
        },
    }
    dto_model = OBJECT_MAPPING[type(domain_object)][dto_type]
    return dto_model.model_validate(domain_object)


class ModelMixin:
    model_config = ConfigDict(from_attributes=True)

    @field_validator(
        "contracts",
        "distributions",
        "access_service",
        mode="before",
        check_fields=False,
    )
    def get_all_from_manager(cls, v: object) -> list | object:
        if isinstance(v, BaseManager):
            return [to_dto(e) for e in v.all()]
        return v

    @field_validator("sources", "sinks", "team", mode="before", check_fields=False)
    def cast_to_id(cls, v: object):
        if isinstance(v, objects.AllObjects):
            return v.id
        return v


class IdMixin:
    """A mixin class that only adds a mandatory id field."""

    id: int


class TeamCreate(ModelMixin, BaseModel):
    """Create view of the team"""

    description: str | None = None
    name: str
    acronym: str
    po_name: str
    po_email: str
    contact_email: str
    scope: str


class Team(IdMixin, TeamCreate):
    """Team Detail view"""


class TeamPartial(ModelMixin, BaseModel):
    """Strictly used for partial updates."""

    name: str | None = None
    description: str | None = None
    acronym: str | None = None
    po_name: str | None = None
    po_email: str | None = None
    contact_email: str | None = None
    scope: str | None = None


class TeamList(ModelMixin, BaseModel):
    id: int
    name: str
    acronym: str


class DataServiceCreateOrUpdate(ModelMixin, BaseModel):
    type: enums.DataServiceType | None = None
    endpoint_url: str | None = None


class DataService(IdMixin, DataServiceCreateOrUpdate):
    """DataService detail view"""


class RefreshPeriod(ModelMixin, BaseModel):
    frequency: int
    unit: enums.TimeUnit


class SetState(ModelMixin, BaseModel):
    publication_status: enums.PublicationStatus


class DistributionCreateOrUpdate(ModelMixin, BaseModel):
    access_service_id: int | None = None
    access_url: str | None = None
    download_url: str | None = None
    format: str | None = None
    filename: str | None = None
    type: enums.DistributionType | None = None
    refresh_period: RefreshPeriod | None = None  # Hoort volgens DCAT op Dataset


class Distribution(IdMixin, DistributionCreateOrUpdate):
    """Distribution detail view"""


class DataContractList(ModelMixin, BaseModel):
    id: int
    publication_status: enums.PublicationStatus | None = None
    name: str | None = None
    description: str | None = None


class DataContractCreateOrUpdate(ModelMixin, BaseModel):
    purpose: str | None = None
    name: str | None = None
    description: str | None = None
    last_updated: datetime | None = None
    privacy_level: enums.PrivacyLevel | None = None
    scope: str | None = None
    confidentiality: enums.ConfidentialityLevel | None = None
    start_date: date | None = None
    retainment_period: int | None = None
    distributions: list[Distribution] | None = None
    tables: list[str] | None = None


class DataContract(IdMixin, DataContractCreateOrUpdate):
    """DataContract detail view"""

    publication_status: enums.PublicationStatus
    missing_fields: list[str] | None = None


class MyContract(ModelMixin, BaseModel):
    id: int
    name: str | None = None
    privacy_level: enums.PrivacyLevel | None = None
    confidentiality: enums.ConfidentialityLevel | None = None
    last_updated: datetime | None = None
    publication_status: enums.PublicationStatus | None = None


class MyProduct(ModelMixin, BaseModel):
    team_id: int
    id: int
    name: str | None = None
    type: enums.ProductType | None = None
    last_updated: datetime | None = None
    publication_status: enums.PublicationStatus | None = None
    contracts: list[MyContract]


class ProductCreate(ModelMixin, BaseModel):
    team_id: int
    name: str | None = Field(None, min_length=2)
    description: str | None = None
    language: enums.Language | None = None
    is_geo: bool | None = None
    crs: enums.CoordRefSystem | None = None
    schema_url: str | None = None
    type: enums.ProductType | None = None
    contracts: list[DataContract] | None = None
    themes: list[enums.Theme] | None = None
    last_updated: datetime | None = None
    refresh_period: RefreshPeriod | None = None
    owner: str | None = None
    contact_email: str | None = None
    data_steward: str | None = None
    services: list[DataService] | None = None
    sources: list[int] | None = None
    sinks: list[int] | None = None


class ProductDetail(IdMixin, ProductCreate):
    """Product detail view"""

    publication_status: enums.PublicationStatus
    missing_fields: list[str] | None = None


class ProductUpdate(ModelMixin, BaseModel):
    """Used for partial update"""

    team_id: int | None = None
    name: str | None = Field(None, min_length=2)
    description: str | None = None
    language: enums.Language | None = None
    is_geo: bool | None = None
    crs: enums.CoordRefSystem | None = None
    schema_url: str | None = None
    type: enums.ProductType | None = None
    contracts: list[DataContract] | None = None
    themes: list[enums.Theme] | None = None
    last_updated: datetime | None = None
    refresh_period: RefreshPeriod | None = None
    owner: str | None = None
    contact_email: str | None = None
    data_steward: str | None = None
    services: list[DataService] | None = None
    sources: list[int] | None = None
    sinks: list[int] | None = None


class ProductList(ModelMixin, BaseModel):
    id: int
    name: str | None = Field(None, min_length=2)
    description: str | None = None
    type: enums.ProductType | None = None
    owner: str | None = None
    themes: list[enums.Theme] | None = None
    last_updated: datetime | None = None
    language: enums.Language | None = None
    summary: dict[str, list[enums.DistributionType | enums.DataServiceType | None]] | None = None
    is_geo: bool | None = None
    schema_url: str | None = None
    publication_status: enums.PublicationStatus | None
    contract_count: int
    team_id: int


class PaginatedResponse[T](BaseModel):
    count: int
    next: str | None
    previous: str | None
    results: list[T]


class MeDetail(BaseModel):
    """Used for openapi spec"""

    teams: list[Team]
    products: PaginatedResponse[MyProduct]


class QueryParams(BaseModel):
    name: str | None = None
    team: int | None = None
    theme: list[enums.Theme] | None = None
    type: list[enums.DistributionType] | None = None
    confidentiality: enums.ConfidentialityLevel | None = None
    publication_status: enums.PublicationStatus | Literal["*"] = enums.PublicationStatus.PUBLISHED
    language: enums.Language | None = None
    order: tuple[str, bool] | None = None
    query: str | None = Field(alias="q", default=None)

    @field_validator("theme", mode="before")
    def validate_themes(cls, raw):
        if not raw:
            return None
        return raw.split(",")

    @field_validator("type", mode="before")
    def validate_type(cls, raw):
        if not raw:
            return None
        return raw.split(",")

    @field_validator("order", mode="before")
    def validate_order(cls, raw):
        if not raw:
            return None
        reversed = raw.startswith("-")
        if reversed:
            return raw[1:], reversed
        else:
            return raw, reversed

    @property
    def filter(self) -> dict:
        result = {}
        for attr in ["team", "theme", "type", "confidentiality", "language", "publication_status"]:
            attr_value = getattr(self, attr)
            if attr_value is not None and attr_value != "*":
                result[attr] = getattr(self, attr)
        return result
