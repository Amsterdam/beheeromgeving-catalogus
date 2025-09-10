from datetime import date, datetime

from django.db.models.manager import BaseManager
from pydantic import BaseModel, ConfigDict, field_validator

from domain.product import enums, objects


def to_response_object(obj: objects.BaseObject | list[objects.BaseObject]) -> dict:
    if isinstance(obj, list):
        return [to_dto(el, dto_type="list").model_dump() for el in obj]
    return to_dto(obj).model_dump()


def to_dto(domain_object: objects.BaseObject, dto_type: str = "detail") -> dict:
    OBJECT_MAPPING = {
        objects.Team: {
            "detail": Team,
            "list": TeamList,
        },
        objects.DataContract: {
            "detail": DataContract,
            "list": DataContractList,
        },
        objects.Product: {
            "detail": ProductDetail,
            "list": ProductList,
        },
        objects.DataService: {
            "detail": DataService,
            "list": DataService,
        },
        objects.Distribution: {
            "detail": Distribution,
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
    def get_all_from_manager(cls, v: object) -> list:
        if isinstance(v, BaseManager):
            return [to_dto(e) for e in v.all()]
        return v

    @field_validator("sources", "sinks", "team", mode="before", check_fields=False)
    def cast_to_id(cls, v: object):
        if isinstance(v, objects.BaseObject):
            return v.id
        return v


class Team(ModelMixin, BaseModel):
    """Used for create and detail views."""

    id: int | None = None
    name: str
    description: str
    acronym: str
    po_name: str
    po_email: str
    contact_email: str
    scope: str


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
    id: int | None = None
    name: str
    acronym: str


class DataService(ModelMixin, BaseModel):
    id: int | None = None
    type: enums.DataServiceType | None = None
    endpoint_url: str | None = None


class Distribution(ModelMixin, BaseModel):
    access_service_id: int | None = None
    access_url: str | None = None
    download_url: str | None = None
    format: str | None = None
    type: enums.DistributionType | None = None
    refresh_period: str | None = None  # Hoort volgens DCAT op Dataset


class DataContractList(ModelMixin, BaseModel):
    id: int | None = None
    publication_status: enums.PublicationStatus | None = None
    name: str | None = None
    description: str | None = None


class DataContract(ModelMixin, BaseModel):
    """Used for create/partial update."""

    id: int | None = None
    publication_status: enums.PublicationStatus | None = None
    purpose: str | None = None
    conditions: str | None = None
    name: str | None = None
    description: str | None = None
    contact_email: str | None = None
    data_steward: str | None = None
    last_updated: datetime | None = None
    has_personal_data: bool | None = None
    has_special_personal_data: bool | None = None
    profile: str | None = None
    confidentiality: enums.ConfidentialityLevel | None = None
    start_date: date | None = None
    retainment_period: int | None = None
    distributions: list[Distribution] | None = None


class ProductDetail(ModelMixin, BaseModel):
    """Used for create/partial update."""

    id: int | None = None
    name: str | None = None
    description: str | None = None
    team_id: int | None = None
    language: enums.Language | None = None
    is_geo: bool | None = None
    schema_url: str | None = None
    type: enums.ProductType | None = None
    contracts: list[DataContract] | None = None
    themes: list[enums.Theme] | None = None
    tags: list[str] | None = None
    last_updated: datetime | None = None
    has_personal_data: bool | None = None
    has_special_personal_data: bool | None = None
    refresh_period: str | None = None
    publication_status: enums.PublicationStatus | None = None
    owner: str | None = None
    services: list[DataService] | None = None
    sources: list[int] | None = None
    sinks: list[int] | None = None


class ProductList(ModelMixin, BaseModel):
    id: int | None = None
    name: str | None = None
    description: str | None = None
    type: enums.ProductType | None = None
