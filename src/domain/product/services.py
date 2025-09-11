from domain import exceptions
from domain.auth import AuthorizationService
from domain.base import (
    AbstractProductRepository,
    AbstractRepository,
    AbstractService,
)
from domain.product import DataContract, DataService, Product


class ProductService:
    repository: AbstractProductRepository
    auth: AuthorizationService

    def __init__(self, repo: AbstractRepository, auth: AbstractService):
        self.repository = repo
        self.auth = auth

    def get_products(self, **kwargs) -> list[Product]:
        return self.repository.list(**kwargs)

    def get_product(self, product_id) -> Product:
        return self.repository.get(product_id)

    def create_product(self, product_data: dict) -> Product:
        if product_data.get("id"):
            raise exceptions.IllegalOperation("IDs are assigned automatically")
        product = Product(**product_data)
        self._persist(product)
        return product

    def update_product(self, product_id: str, updated_product: dict) -> Product:
        if int(updated_product.get("id", product_id)) != int(product_id):
            raise exceptions.IllegalOperation("Cannot update product id")

        existing_product = self.get_product(product_id)
        existing_product.update_from_dict(updated_product)
        self._persist(existing_product)
        return existing_product.id

    def delete_product(self, product_id: int) -> None:
        self.repository.delete(product_id)

    def get_contracts(self, product_id: int) -> list[DataContract]:
        return self.repository.get(product_id).contracts

    def get_contract(self, product_id: int, contract_id: int) -> DataContract:
        try:
            return next(
                contract
                for contract in (self.get_contracts(product_id) or [])
                if contract.id == contract_id
            )
        except StopIteration:
            raise exceptions.ObjectDoesNotExist(
                f"Contract with id {contract_id} does not exist on Product {product_id}"
            ) from None

    def create_contract(self, product_id: int, contract_data: int):
        if contract_data.get("id"):
            raise exceptions.IllegalOperation("IDs are assigned automatically")

        product = self.get_product(product_id)
        contract = DataContract(**contract_data)
        if product.contracts:
            product.contracts.append(contract)
        else:
            product.contracts = [contract]
        self._persist(product)
        return contract

    def update_contract(self, product_id: int, contract_id: int, contract_data: dict):
        if int(contract_data.get("id", contract_id)) != int(contract_id):
            raise exceptions.IllegalOperation("Cannot update contract id")

        product = self.get_product(product_id)
        try:
            contract = next(
                contract
                for contract in (product.contracts or [])
                if contract.id == int(contract_id)
            )
        except StopIteration:
            raise exceptions.ObjectDoesNotExist(
                f"Contract with id {contract_id} does not exist on Product {product_id}"
            ) from None
        contract.update_from_dict(contract_data)
        self._persist(product)
        return contract

    def delete_contract(self, product_id: int, contract_id: int):
        product = self.get_product(product_id)
        contract_ids = [c.id for c in product.contracts]
        if contract_id not in contract_ids:
            raise exceptions.ObjectDoesNotExist(
                f"Contract with id {contract_id} does not exist on Product {product_id}"
            ) from None
        product.contracts = [
            contract for contract in product.contracts if contract.id != contract_id
        ]
        self._persist(product)

    def get_services(self, product_id: int) -> list[DataService]:
        return self.repository.get(product_id).services

    def get_service(self, product_id: int, service_id: int) -> DataService:
        try:
            return next(
                service
                for service in (self.get_services(product_id) or [])
                if service.id == int(service_id)
            )
        except StopIteration:
            raise exceptions.ObjectDoesNotExist(
                f"Service with id {service_id} does not exist on Product {product_id}"
            ) from None

    def create_service(self, product_id: int, service_data: int) -> DataService:
        if service_data.get("id"):
            raise exceptions.IllegalOperation("IDs are assigned automatically")

        product = self.get_product(product_id)
        service = DataService(**service_data)
        if product.services:
            product.services.append(service)
        else:
            product.services = [service]
        self._persist(product)
        return service

    def update_service(self, product_id: int, service_id: int, service_data: dict) -> DataService:
        if int(service_data.get("id", service_id)) != int(service_id):
            raise exceptions.IllegalOperation("Cannot update service id")

        product = self.get_product(product_id)
        try:
            service = next(
                service for service in (product.services or []) if service.id == int(service_id)
            )
        except StopIteration:
            raise exceptions.ObjectDoesNotExist(
                f"Service with id {service_id} does not exist on Product {product_id}"
            ) from None
        service.update_from_dict(service_data)
        self._persist(product)
        return service

    def delete_service(self, product_id: int, service_id: int):
        product = self.get_product(product_id)
        service_ids = [s.id for s in product.services]
        if service_id not in service_ids:
            raise exceptions.ObjectDoesNotExist(
                f"Service with id {service_id} does not exist on Product {product_id}"
            ) from None
        product.services = [
            service for service in product.services if service.id != int(service_id)
        ]
        self._persist(product)
        return service_id

    def _persist(self, product: Product):
        return self.repository.save(product)
