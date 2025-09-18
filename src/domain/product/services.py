from domain import exceptions
from domain.auth import authorize
from domain.base import AbstractProductRepository, AbstractRepository, AbstractService
from domain.product import DataContract, DataService, Product


class ProductService(AbstractService):
    repository: AbstractProductRepository

    def __init__(self, repo: AbstractRepository):
        self.repository = repo

    def get_products(self, **kwargs) -> list[Product]:
        return self.repository.list(**kwargs)

    def get_product(self, product_id: int) -> Product:
        return self.repository.get(product_id)

    @authorize.is_team_member
    def create_product(self, *, data: dict, **kwargs) -> Product:
        if data.get("id"):
            raise exceptions.IllegalOperation("IDs are assigned automatically")
        product = Product(**data)
        return self._persist(product)

    @authorize.is_team_member
    def update_product(self, *, product_id: int, data: dict, **kwargs) -> Product:
        if data.get("id", product_id) != product_id:
            raise exceptions.IllegalOperation("Cannot update product id")

        existing_product = self.get_product(product_id)
        existing_product.update_from_dict(data)
        self._persist(existing_product)
        return existing_product.id

    @authorize.is_team_member
    def delete_product(self, *, product_id: int, **kwargs) -> None:
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

    @authorize.is_team_member
    def create_contract(self, product_id: int, data: int, **kwargs) -> DataContract:
        if data.get("id"):
            raise exceptions.IllegalOperation("IDs are assigned automatically")

        product = self.get_product(product_id)
        contract = DataContract(**data)
        product.create_contract(contract)
        self._persist(product)
        return contract

    @authorize.is_team_member
    def update_contract(
        self, product_id: int, contract_id: int, data: dict, **kwargs
    ) -> DataContract:
        if data.get("id", contract_id) != contract_id:
            raise exceptions.IllegalOperation("Cannot update contract id")

        product = self.get_product(product_id)
        try:
            contract = next(
                contract for contract in (product.contracts or []) if contract.id == contract_id
            )
        except StopIteration:
            raise exceptions.ObjectDoesNotExist(
                f"Contract with id {contract_id} does not exist on Product {product_id}"
            ) from None
        contract.update_from_dict(data)
        self._persist(product)
        return contract

    @authorize.is_team_member
    def delete_contract(self, product_id: int, contract_id: int, **kwargs):
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
                if service.id == service_id
            )
        except StopIteration:
            raise exceptions.ObjectDoesNotExist(
                f"Service with id {service_id} does not exist on Product {product_id}"
            ) from None

    @authorize.is_team_member
    def create_service(self, product_id: int, data: int, **kwargs) -> DataService:
        if data.get("id"):
            raise exceptions.IllegalOperation("IDs are assigned automatically")

        product = self.get_product(product_id)
        service = DataService(**data)
        if product.services:
            product.services.append(service)
        else:
            product.services = [service]
        self._persist(product)
        return service

    @authorize.is_team_member
    def update_service(
        self, product_id: int, service_id: int, data: dict, **kwargs
    ) -> DataService:
        if data.get("id", service_id) != service_id:
            raise exceptions.IllegalOperation("Cannot update service id")

        product = self.get_product(product_id)
        try:
            service = next(
                service for service in (product.services or []) if service.id == service_id
            )
        except StopIteration:
            raise exceptions.ObjectDoesNotExist(
                f"Service with id {service_id} does not exist on Product {product_id}"
            ) from None
        service.update_from_dict(data)
        self._persist(product)
        return service

    @authorize.is_team_member
    def delete_service(self, product_id: int, service_id: int, **kwargs) -> int:
        product = self.get_product(product_id)
        service_ids = [s.id for s in product.services]
        if service_id not in service_ids:
            raise exceptions.ObjectDoesNotExist(
                f"Service with id {service_id} does not exist on Product {product_id}"
            ) from None
        product.services = [service for service in product.services if service.id != service_id]
        self._persist(product)
        return service_id

    def _persist(self, product: Product) -> Product:
        return self.repository.save(product)
