from domain.auth import authorize
from domain.base import AbstractRepository, AbstractService
from domain.product import (
    DataContract,
    DataService,
    Distribution,
    Product,
    RefreshPeriod,
    enums,
)


class ProductService(AbstractService):
    repository: AbstractRepository[Product]

    def __init__(self, repo: AbstractRepository[Product]):
        self.repository = repo

    def get_products(self, **kwargs) -> list[Product]:
        return self.repository.list(**kwargs)

    def get_product(self, product_id: int) -> Product:
        return self.repository.get(product_id)

    @authorize.is_team_member
    def create_product(self, *, data: dict, **kwargs) -> Product:
        refresh_period = data.pop("refresh_period", None)
        product = Product(
            **data,
            refresh_period=(RefreshPeriod.from_dict(refresh_period) if refresh_period else None),
            publication_status=enums.PublicationStatus.DRAFT,
        )
        return self._persist(product)

    @authorize.is_team_member
    def update_product(self, *, product_id: int, data: dict, **kwargs) -> Product:
        existing_product = self.get_product(product_id)
        if data.get("refresh_period"):
            data["refresh_period"] = RefreshPeriod.from_dict(data["refresh_period"])
        existing_product.update_from_dict(data)
        return self._persist(existing_product)

    @authorize.is_team_member
    def delete_product(self, *, product_id: int, **kwargs) -> None:
        self.repository.delete(product_id)

    def get_contracts(self, product_id: int) -> list[DataContract]:
        return self.repository.get(product_id).contracts

    def get_contract(self, product_id: int, contract_id: int) -> DataContract:
        product = self.repository.get(product_id)
        return product.get_contract(contract_id)

    @authorize.is_team_member
    def create_contract(self, product_id: int, data: dict, **kwargs) -> DataContract:
        product = self.get_product(product_id)
        contract = DataContract(**data)
        product.create_contract(contract)
        updated_product = self._persist(product)
        return updated_product.contracts[-1]

    @authorize.is_team_member
    def update_contract(
        self, product_id: int, contract_id: int, data: dict, **kwargs
    ) -> DataContract:
        product = self.get_product(product_id)
        contract = product.update_contract(contract_id, data)
        self._persist(product)
        return contract

    @authorize.is_team_member
    def delete_contract(self, product_id: int, contract_id: int, **kwargs):
        product = self.get_product(product_id)
        product.delete_contract(contract_id)
        self._persist(product)

    @authorize.is_team_member
    def update_publication_status(self, product_id: int, data: dict, **kwargs) -> Product:
        existing_product = self.repository.get(product_id)
        existing_product.update_state(data)
        return self._persist(existing_product)

    def get_distributions(self, product_id: int, contract_id: int) -> list[Distribution]:
        product = self.repository.get(product_id)
        return product.get_contract(contract_id).distributions

    def get_distribution(
        self, product_id: int, contract_id: int, distribution_id: int
    ) -> Distribution:
        product = self.repository.get(product_id)
        return product.get_distribution(contract_id=contract_id, distribution_id=distribution_id)

    @authorize.is_team_member
    def create_distribution(
        self, *, product_id: int, contract_id: int, data: dict, **kwargs
    ) -> Distribution:
        product = self.get_product(product_id)
        refresh_period = data.pop("refresh_period", None)
        distribution = Distribution(
            **data,
            refresh_period=(RefreshPeriod.from_dict(refresh_period) if refresh_period else None),
        )
        product.add_distribution_to_contract(contract_id, distribution)
        self._persist(product)
        updated_product = self.get_product(product_id)
        return updated_product.get_contract(contract_id).distributions[-1]

    @authorize.is_team_member
    def update_distribution(
        self, *, product_id: int, contract_id: int, distribution_id: int, data: dict, **kwargs
    ) -> Distribution:
        product = self.repository.get(product_id)
        distribution = product.update_distribution(contract_id, distribution_id, data)
        self._persist(product)
        return distribution

    @authorize.is_team_member
    def delete_distribution(
        self, product_id: int, contract_id: int, distribution_id: int, **kwargs
    ) -> DataContract:
        product = self.repository.get(product_id)
        product.delete_distribution(contract_id, distribution_id)
        self._persist(product)
        return distribution_id

    def get_services(self, product_id: int) -> list[DataService]:
        product = self.repository.get(product_id)
        return product.services

    def get_service(self, product_id: int, service_id: int) -> DataService:
        product = self.repository.get(product_id)
        return product.get_service(service_id)

    @authorize.is_team_member
    def create_service(self, product_id: int, data: dict, **kwargs) -> DataService:
        product = self.get_product(product_id)
        product.create_service(data)
        updated_product = self._persist(product)
        return updated_product.services[-1]

    @authorize.is_team_member
    def update_service(
        self, product_id: int, service_id: int, data: dict, **kwargs
    ) -> DataService:
        product = self.get_product(product_id)
        service = product.update_service(service_id, data)
        self._persist(product)
        return service

    @authorize.is_team_member
    def delete_service(self, product_id: int, service_id: int, **kwargs) -> int:
        product = self.get_product(product_id)
        product.delete_service(service_id)
        self._persist(product)
        return service_id

    def _persist(self, product: Product) -> Product:
        return self.repository.save(product)
