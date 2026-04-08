from collections.abc import Sequence
from datetime import date, datetime
from typing import TYPE_CHECKING, Literal, overload

from pydantic import BaseModel, ConfigDict, Field, field_validator

from domain.base import BaseObject
from domain.product import enums, objects
from domain.team import Team as DomainTeam

if TYPE_CHECKING:
    from beheeromgeving.models import DataContract as ORMDataContract
    from beheeromgeving.models import Product as ORMProduct


def has_unpublished_changes_for_orm(product: ORMProduct) -> bool:
    """True when working copy is newer than the last published snapshot."""
    record = getattr(product, "published_snapshot_record", None)
    if not record or not record.published_at:
        return False
    if product.last_updated > record.published_at:
        return True
    return any(c.last_updated > record.published_at for c in product.contracts.order_by("id"))


@overload
def to_response_object(obj: Sequence[BaseObject], dto_type: str | None = None) -> list[dict]: ...


@overload
def to_response_object(obj: BaseObject, dto_type: str | None = None) -> dict: ...


def to_response_object(
    obj: BaseObject | Sequence[BaseObject], dto_type: str | None = None
) -> dict | list[dict]:
    if not isinstance(obj, BaseObject):
        return [to_dto(el, dto_type=dto_type or "list").model_dump() for el in obj]
    dt = dto_type or "detail"
    dto = to_dto(obj, dto_type=dt)
    data = dto.model_dump()
    if isinstance(obj, objects.Product) and dt == "detail" and obj.id is not None:
        from beheeromgeving.models import Product as ORMProduct

        try:
            orm_p = ORMProduct.objects.select_related("published_snapshot_record").get(pk=obj.id)
            data["has_unpublished_changes"] = has_unpublished_changes_for_orm(orm_p)
        except ORMProduct.DoesNotExist:
            pass
    return data


def to_dto(domain_object: BaseObject, dto_type: str = "detail") -> BaseModel:
    OBJECT_MAPPING: dict[type[BaseObject], dict[str, type[BaseModel]]] = {
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


class Team(IdMixin, ModelMixin, BaseModel):
    """Team Detail view"""

    description: str | None = None
    name: str
    acronym: str
    po_name: str
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
    crs: list[enums.CoordRefSystem] | None = None


class Distribution(IdMixin, DistributionCreateOrUpdate):
    """Distribution detail view"""


class DataContractList(ModelMixin, BaseModel):
    id: int
    publication_status: enums.PublicationStatus | None = None
    name: str | None = None
    description: str | None = None
    confidentiality: enums.ConfidentialityLevel | None = None


class DataContractCreateOrUpdate(ModelMixin, BaseModel):
    purpose: str | None = None
    name: str | None = None
    description: str | None = None
    last_updated: datetime | None = None
    privacy_level: enums.PrivacyLevel | None = None
    scopes: list[str] | None = None
    confidentiality: enums.ConfidentialityLevel | None = None
    start_date: date | None = None
    retainment_period: int | None = None
    distributions: list[Distribution] | None = None
    tables: list[str] | None = None


class DataContract(IdMixin, DataContractCreateOrUpdate):
    """DataContract detail view"""

    publication_status: enums.PublicationStatus
    missing_fields: list[str] | None = None
    schema_url: str | None = None


class MyContract(ModelMixin, BaseModel):
    id: int
    name: str | None = None
    privacy_level: enums.PrivacyLevel | None = None
    confidentiality: enums.ConfidentialityLevel | None = None
    last_updated: datetime | None = None
    publication_status: enums.PublicationStatus | None = None

    @classmethod
    def from_django(cls, contract: ORMDataContract) -> MyContract:
        return cls(
            id=contract.pk,
            name=contract.name,
            privacy_level=contract.privacy_level,
            confidentiality=contract.confidentiality,
            last_updated=contract.last_updated,
            publication_status=contract.publication_status,
        )


class MyProduct(ModelMixin, BaseModel):
    team_id: int
    id: int
    name: str | None = None
    type: enums.ProductType | None = None
    last_updated: datetime | None = None
    publication_status: enums.PublicationStatus | None = None
    contracts: list[MyContract]
    has_unpublished_changes: bool = False

    @classmethod
    def from_django(cls, product: ORMProduct) -> MyProduct:
        dirty = has_unpublished_changes_for_orm(product)
        return cls(
            id=product.pk,
            team_id=product.team.pk,
            name=product.name,
            type=product.type,
            last_updated=product.last_updated,
            publication_status=product.publication_status,
            contracts=[MyContract.from_django(c) for c in product.contracts.order_by("id")],
            has_unpublished_changes=dirty,
        )


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
    has_unpublished_changes: bool = False


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

    @classmethod
    def from_django(cls, product: ORMProduct) -> ProductList:
        return cls(
            id=product.pk,
            name=product.name,
            description=product.description,
            type=product.type,
            owner=product.owner,
            themes=product.themes,
            last_updated=product.last_updated,
            language=product.language,
            is_geo=product.is_geo,
            schema_url=product.schema_url,
            publication_status=product.publication_status,
            contract_count=product.contracts.filter(
                publication_status=enums.PublicationStatus.PUBLISHED.value
            ).count(),
            team_id=product.team.pk,
            summary={
                "services": [s.type for s in product.services.all() if s.type is not None],
                "distributions": [
                    d.type
                    for c in product.contracts.all()
                    for d in c.distributions.all()
                    if d.type is not None and d.type != enums.DistributionType.API.value
                ],
            },
        )


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
    team: list[int] | None = None
    theme: list[enums.Theme] | None = None
    type: list[enums.DistributionType] | None = None
    confidentiality: list[enums.ConfidentialityLevel] | None = None
    publication_status: enums.PublicationStatus | Literal["*"] = enums.PublicationStatus.PUBLISHED
    language: list[enums.Language] | None = None
    order: tuple[str, bool] | None = None
    query: str | None = Field(alias="q", default=None)
    is_geo: bool | None = None
    has_schema_url: bool | None = None

    @field_validator("theme", mode="before")
    def validate_themes(cls, raw):
        if not raw:
            return None
        return raw.split(",")

    @field_validator("confidentiality", mode="before")
    def validate_confidentiality(cls, raw):
        if not raw:
            return None
        return raw.split(",")

    @field_validator("language", mode="before")
    def validate_language(cls, raw):
        if not raw:
            return None
        return raw.split(",")

    @field_validator("team", mode="before")
    def validate_team(cls, raw):
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
        for attr, lookup in {
            "team": "team_id__in",
            "theme": "themes__overlap",
            "type": "contracts__distributions__type__in",
            "confidentiality": "contracts__confidentiality__in",
            "language": "language__in",
            "publication_status": "publication_status",
            "is_geo": "is_geo",
        }.items():
            attr_value = getattr(self, attr)
            if attr_value is not None and attr_value != "*":
                result[lookup] = attr_value
        return result

    @property
    def exclude(self) -> dict:
        if self.has_schema_url is True:
            return {"schema_url__exact": ""}
        elif self.has_schema_url is False:
            return {"schema_url__regex": r"schema"}
        return {}
