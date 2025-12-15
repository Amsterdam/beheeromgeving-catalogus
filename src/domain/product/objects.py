from dataclasses import dataclass, field
from datetime import date, datetime

from domain.base import BaseObject
from domain.exceptions import ObjectDoesNotExist, ValidationError
from domain.product import enums


@dataclass
class RefreshPeriod:
    frequency: int
    unit: enums.TimeUnit

    @property
    def to_string(self):
        return f"{self.frequency}.{self.unit.value}"

    @classmethod
    def from_dict(cls, data: dict):
        frequency = data["frequency"]
        unit = enums.TimeUnit[data["unit"]]
        return cls(frequency=frequency, unit=unit)

    @classmethod
    def from_string(cls, str_value):
        try:
            frequency, unit = str_value.split(".")
            return cls(frequency, enums.TimeUnit[unit])
        except KeyError:
            return None


@dataclass(kw_only=True)
class DataService(BaseObject):
    id: int | None = None
    type: enums.DataServiceType | None = None
    endpoint_url: str | None = None

    _skip_keys = set()


@dataclass(kw_only=True)
class Distribution(BaseObject):
    id: int | None = None
    access_service_id: int | None = None
    access_url: str | None = None
    download_url: str | None = None
    format: str | None = None
    filename: str | None = None
    type: enums.DistributionType | None = None
    refresh_period: RefreshPeriod | None = None

    _skip_keys = {"refresh_period"}


class ContractValidator:
    def __init__(self, datacontract: "DataContract"):
        self.contract = datacontract

    def get_missing_fields(self) -> list[str]:
        required_fields = [
            "name",
            "description",
            "purpose",
            "confidentiality",
            "privacy_level",
            "retainment_period",
            "start_date",
            "scope",
        ]
        return [field for field in required_fields if getattr(self.contract, field) is None]

    def can_change_publication_status(self, data: dict) -> True:
        missing_fields = self.get_missing_fields()
        if (
            data.get("publication_status") == "P"
            and missing_fields
            and self.contract.publication_status != enums.PublicationStatus.PUBLISHED
        ):
            raise ValidationError(
                "Cannot update publication status, contract is missing the following fields:"
                f"[{", ".join(missing_fields)}]"
            )

        return True


@dataclass(kw_only=True)
class DataContract(BaseObject):
    id: int | None = None
    publication_status: enums.PublicationStatus | None = None
    purpose: str | None = None
    name: str | None = None
    description: str | None = None
    last_updated: datetime | None = None
    privacy_level: enums.PrivacyLevel | None = None
    scope: str | None = None
    confidentiality: enums.ConfidentialityLevel | None = None
    start_date: date | None = None
    retainment_period: int | None = None
    distributions: list[Distribution] = field(default_factory=list)

    _skip_keys = {"contact_email", "distributions"}

    def __post_init__(self):
        self.validate = ContractValidator(self)

    @property
    def missing_fields(self) -> list[str]:
        return self.validate.get_missing_fields()


class ProductValidator:
    def __init__(self, prod: "Product"):
        self.product = prod

    def can_create_contract(self) -> True:
        required_fields = [
            "name",
            "type",
            "privacy_level",
        ]
        missing_fields = [
            field for field in required_fields if getattr(self.product, field) is None
        ]
        if missing_fields:
            raise ValidationError(
                "Cannot create contract, product is missing the following fields:"
                f"[{", ".join(missing_fields)}]"
            )
        return True

    def get_missing_fields(self) -> list[str]:
        required_fields = [
            "name",
            "description",
            "team_id",
            "language",
            "is_geo",
            "crs",
            "schema_url",
            "themes",
            "privacy_level",
            "refresh_period",
            "contact_email",
        ]
        return [field for field in required_fields if getattr(self.product, field) is None]

    def can_change_publication_status(self, data: dict) -> True:
        missing_fields = self.get_missing_fields()
        if (
            data.get("publication_status") == "P"
            and missing_fields
            and self.product.publication_status != enums.PublicationStatus.PUBLISHED
        ):
            raise ValidationError(
                "Cannot update publication status, product is missing the following fields:"
                f"[{", ".join(missing_fields)}]"
            )

        return True


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
    contracts: list[DataContract] = field(default_factory=list)
    themes: list[enums.Theme] | None = None
    last_updated: datetime | None = None
    created_at: datetime | None = None
    privacy_level: enums.PrivacyLevel | None = None
    refresh_period: RefreshPeriod | None = None
    publication_status: enums.PublicationStatus | None = None
    owner: str | None = None
    contact_email: str | None = None
    data_steward: str | None = None
    services: list[DataService] = field(default_factory=list)
    sources: list[int] = field(default_factory=list)
    sinks: list[int] = field(default_factory=list)

    _skip_keys = {"contracts", "team", "owner", "refresh_period", "sources", "sinks", "services"}

    def __post_init__(self):
        self.validate = ProductValidator(self)

    def create_contract(self, contract: DataContract):
        if self.validate.can_create_contract():
            self.contracts.append(contract)

    def get_contract(self, contract_id: int):
        try:
            return next(contract for contract in self.contracts if contract.id == contract_id)
        except StopIteration:
            raise ObjectDoesNotExist(
                f"contract with id {contract_id} does not exist on product {self.id}"
            ) from None

    def get_service(self, service_id: int):
        try:
            return next(service for service in self.services if service.id == service_id)
        except StopIteration:
            raise ObjectDoesNotExist(
                f"service with id {service_id} does not exist on product {self.id}"
            ) from None

    def update_state(self, data: dict):
        if self.validate.can_change_publication_status(data):
            self.update_from_dict(data)
        return self

    def update_contract(self, contract_id: int, data: dict) -> DataContract:
        contract = self.get_contract(contract_id)
        contract.update_from_dict(data)
        return contract

    def update_contract_state(self, contract_id: int, data: dict) -> DataContract:
        contract = self.get_contract(contract_id)
        if contract.validate.can_change_publication_status(data):
            contract.update_from_dict(data)
        return contract

    def delete_contract(self, contract_id: int) -> int:
        self.get_contract(contract_id)  # Raise if it doesn't exist.
        self.contracts = [contract for contract in self.contracts if contract.id != contract_id]
        return contract_id

    def get_distribution(self, contract_id: int, distribution_id: int):
        contract = self.get_contract(contract_id)
        try:
            return next(dist for dist in contract.distributions if dist.id == distribution_id)
        except StopIteration:
            raise ObjectDoesNotExist(
                f"Distribution with id {distribution_id} does not exist on contract"
                f"with id {contract_id}"
            ) from None

    def add_distribution_to_contract(self, contract_id: int, distribution: Distribution) -> None:
        contract = self.get_contract(contract_id)
        contract.distributions.append(distribution)

    def update_distribution(
        self, contract_id: int, distribution_id: int, data: dict
    ) -> Distribution:
        distribution = self.get_distribution(contract_id, distribution_id)
        distribution.update_from_dict(data)
        if refresh_period := data.get("refresh_period"):
            distribution.refresh_period = RefreshPeriod(**refresh_period)
        return distribution

    def delete_distribution(self, contract_id: int, distribution_id: int) -> int:
        self.get_distribution(contract_id, distribution_id)  # Raises if it doesn't exist.
        contract = self.get_contract(contract_id)
        contract.distributions = [
            distribution
            for distribution in contract.distributions
            if distribution.id != distribution_id
        ]
        return distribution_id

    def create_service(self, data: dict) -> DataService:
        service = DataService(**data)
        self.services.append(service)
        return service

    def update_service(self, service_id: int, data: dict) -> DataService:
        service = self.get_service(service_id)
        service.update_from_dict(data)
        return service

    def delete_service(self, service_id: int) -> int:
        self.get_service(service_id)  # Raises if it doesn't exist
        if any(
            distribution.access_service_id == service_id
            for contract in self.contracts
            for distribution in contract.distributions
        ):
            raise ValidationError("Cannot delete service, it is still in use by distributions")
        service_ids = [s.id for s in self.services]
        if service_id not in service_ids:
            raise ObjectDoesNotExist(
                f"Service with id {service_id} does not exist on Product {self.id}"
            ) from None
        self.services = [service for service in self.services if service.id != service_id]
        return service_id

    @property
    def summary(self) -> dict[str, list[enums.StrEnum]]:
        return {
            "services": [service.type for service in self.services if service.type is not None],
            "distributions": [
                distribution.type
                for contract in self.contracts
                for distribution in contract.distributions
                if distribution.type != enums.DistributionType.API
                and distribution.type is not None
            ],
        }

    @property
    def contract_count(self) -> int:
        return len(self.contracts)

    @property
    def search_string(self) -> str:
        result = ""
        if self.name:
            result += self.name + " "
        if self.description:
            result += self.description + " "
        for contract in self.contracts:
            if contract.name:
                result += contract.name + " "
            if contract.description:
                result += contract.description + " "
        return result.lower()

    def matches_filter(self, filter: dict) -> bool:
        """
        Filter on several attributes.

        These attributes are mutually additive - if multiple are given, all must apply.
        However, if multiple values are available on a product for a certain attribute,
        only one needs to match.
        """
        team_id = filter.get("team")
        if team_id is not None and team_id != self.team_id:
            return False
        themes = filter.get("theme")
        if themes is not None and not any(theme in (self.themes or []) for theme in themes):
            return False
        language = filter.get("language")
        if language is not None and self.language != language:
            return False
        confidentiality = filter.get("confidentiality")
        if confidentiality is not None and not any(
            contract.confidentiality == confidentiality for contract in self.contracts
        ):
            return False
        dist_type = filter.get("type")
        if dist_type is not None and not any(  # noqa: SIM103
            distribution.type in dist_type
            for contract in self.contracts
            for distribution in contract.distributions
        ):
            return False

        return True

    @property
    def missing_fields(self) -> list[str]:
        return self.validate.get_missing_fields()


AllObjects = Product | DataContract | DataService | Distribution
