from dataclasses import dataclass
from datetime import date, datetime

from domain.base import BaseObject
from domain.product import enums


@dataclass(kw_only=True)
class DataService(BaseObject):
    id: int | None = None
    type: enums.DataServiceType | None = None
    endpoint_url: str | None = None

    _skip_keys = set()


@dataclass(kw_only=True)
class Distribution(BaseObject):
    access_service_id: int | None = None
    access_url: str | None = None
    download_url: str | None = None
    format: str | None = None
    type: enums.DistributionType | None = None
    refresh_period: str | None = None  # Hoort volgens DCAT op Dataset

    _skip_keys = set()


@dataclass(kw_only=True)
class DataContract(BaseObject):
    id: int | None = None
    publication_status: enums.PublicationStatus | None = None
    purpose: str | None = None
    name: str | None = None
    description: str | None = None
    contact_email: str | None = None
    data_steward: str | None = None
    last_updated: datetime | None = None
    has_personal_data: bool | None = None
    has_special_personal_data: bool | None = None
    scope: str | None = None
    confidentiality: enums.ConfidentialityLevel | None = None
    start_date: date | None = None
    retainment_period: int | None = None
    distributions: list[Distribution] | None = None

    _skip_keys = {"contact_email", "distributions"}

    def update_from_dict(self, data):
        super().update_from_dict(data)
        self.distributions = [
            Distribution(**distribution) for distribution in data.get("distribution", [])
        ]


@dataclass
class RefreshPeriod:
    frequency: int
    unit: enums.TimeUnit


@dataclass(kw_only=True)
class Product(BaseObject):
    id: int | None = None
    name: str | None = None
    description: str | None = None
    team_id: int | None = None
    language: enums.Language | None = None
    is_geo: bool | None = None
    crs: enums.CoordRefSystem | None = None
    schema_url: str | None = None
    type: enums.ProductType | None = None
    contracts: list[DataContract] | None = None
    themes: list[enums.Theme] | None = None
    last_updated: datetime | None = None
    has_personal_data: bool | None = None
    has_special_personal_data: bool | None = None
    refresh_period: RefreshPeriod | None = None
    publication_status: enums.PublicationStatus | None = None
    owner: str | None = None
    services: list[DataService] | None = None
    sources: list[int] = None
    sinks: list[int] = None

    _skip_keys = {"contracts", "team", "owner", "sources", "sinks", "services"}
