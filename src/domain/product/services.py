from domain import exceptions
from domain.auth import ProductId, Scope, authorize
from domain.base import AbstractRepository, AbstractService
from domain.product import (
    DataContract,
    DataService,
    Distribution,
    Product,
    RefreshPeriod,
    enums,
)
from domain.product.policies import ProductReadLevel, ProductReadPolicy


class ProductService(AbstractService):
    repository: AbstractRepository[Product]

    def __init__(self, repo: AbstractRepository[Product]):
        self.repository = repo
        if authorize.auth is None:
            raise exceptions.DomainException(
                "Authorizer doesn't have an AuthorizationService, please call set_auth_service()"
            )
        self.auth = authorize.auth

    @authorize.is_admin
    def get_all_products(self, **kwargs) -> list[Product]:
        return self.repository.list_all()

    def get_product(
        self,
        product_id: int,
        *,
        scopes: list[Scope] | None = None,
        **kwargs,
    ) -> Product:
        policy = ProductReadPolicy(auth=self.auth)
        level = policy.level_for_product(product_id=ProductId(product_id), scopes=scopes)
        if level is ProductReadLevel.FULL:
            return self.repository.get(product_id)
        if level is ProductReadLevel.INTERNAL:
            return self.repository.get_for_publication_status(
                product_id,
                [
                    enums.PublicationStatus.PUBLISHED,
                    enums.PublicationStatus.INTERNALLY_PUBLISHED,
                ],
            )
        return self.repository.get_for_publication_status(
            product_id,
            [enums.PublicationStatus.PUBLISHED],
        )

    def get_product_by_name(
        self,
        name: str,
        *,
        scopes: list[Scope] | None = None,
        **kwargs,
    ) -> Product:
        policy = ProductReadPolicy(auth=self.auth)
        level = policy.level_for_product_name(name=name, scopes=scopes)
        if level is ProductReadLevel.FULL:
            return self.repository.get_by_name(name)
        if level is ProductReadLevel.INTERNAL:
            return self.repository.get_for_publication_status_by_name(
                name,
                [
                    enums.PublicationStatus.PUBLISHED,
                    enums.PublicationStatus.INTERNALLY_PUBLISHED,
                ],
            )
        return self.repository.get_for_publication_status_by_name(
            name,
            [enums.PublicationStatus.PUBLISHED],
        )

    @authorize.is_admin
    @authorize.is_team_member
    def create_product(self, *, data: dict, **kwargs) -> Product:
        refresh_period = data.pop("refresh_period", None)
        product = Product(
            **data,
            refresh_period=(RefreshPeriod.from_dict(refresh_period) if refresh_period else None),
            publication_status=enums.PublicationStatus.DRAFT,
            last_editor="import",
        )
        return self._persist(product)

    @authorize.is_admin
    @authorize.is_team_member
    def update_product(self, *, product_id: int, data: dict, **kwargs) -> Product:
        existing_product = self.get_product(product_id=product_id, **kwargs)
        if data.get("refresh_period"):
            data["refresh_period"] = RefreshPeriod.from_dict(data["refresh_period"])
        if kwargs.get("last_editor"):
            data["last_editor"] = kwargs["last_editor"]
        existing_product.update(data)
        return self._persist(existing_product)

    @authorize.is_admin
    @authorize.is_team_member
    def delete_product(self, *, product_id: int, **kwargs) -> None:
        product = self.get_product(product_id=product_id, **kwargs)
        if product.publication_date is not None:
            product.update_state({"publication_status": enums.PublicationStatus.DELETED})
            for contract in product.contracts:
                if contract.id:
                    product.delete_contract(contract.id)
            self._persist(product)
        else:
            self.repository.delete(product_id)

    def get_contracts(
        self,
        product_id: int,
        *,
        scopes: list[Scope] | None = None,
        **kwargs,
    ) -> list[DataContract]:
        product = self.get_product(product_id=product_id, scopes=scopes, **kwargs)
        return product.contracts

    def get_contract(
        self,
        product_id: int,
        contract_id: int,
        *,
        scopes: list[Scope] | None = None,
        **kwargs,
    ) -> DataContract:
        product = self.get_product(product_id=product_id, scopes=scopes, **kwargs)
        return product.get_contract(contract_id)

    @authorize.is_admin
    @authorize.is_team_member
    def create_contract(self, product_id: int, data: dict, **kwargs) -> DataContract:
        product = self.get_product(product_id=product_id, **kwargs)
        contract = DataContract(
            **data,
            publication_status=enums.PublicationStatus.DRAFT,
            last_editor="import",
        )
        product.create_contract(contract)
        updated_product = self._persist(product)
        return updated_product.contracts[-1]

    @authorize.is_admin
    @authorize.is_team_member
    def update_contract(
        self, product_id: int, contract_id: int, data: dict, **kwargs
    ) -> DataContract:
        product = self.get_product(product_id=product_id, **kwargs)
        if kwargs.get("last_editor"):
            data["last_editor"] = kwargs["last_editor"]
        contract = product.update_contract(contract_id, data)
        self._persist(product)
        return contract

    @authorize.is_admin
    @authorize.is_team_member
    def update_contract_publication_status(
        self, product_id: int, contract_id: int, data: dict, **kwargs
    ) -> DataContract:
        product = self.get_product(product_id=product_id, **kwargs)
        updated_contract = product.update_contract_state(contract_id, data)
        self._persist(product)
        return updated_contract

    @authorize.is_admin
    @authorize.is_team_member
    def delete_contract(self, product_id: int, contract_id: int, **kwargs):
        product = self.get_product(product_id=product_id, **kwargs)
        product.delete_contract(contract_id)
        self._persist(product)

    @authorize.is_admin
    @authorize.is_team_member
    def update_publication_status(self, product_id: int, data: dict, **kwargs) -> Product:
        existing_product = self.repository.get(product_id)
        existing_product.update_state(data)
        return self._persist(existing_product)

    def get_distributions(
        self,
        product_id: int,
        contract_id: int,
        *,
        scopes: list[Scope] | None = None,
        **kwargs,
    ) -> list[Distribution]:
        product = self.get_product(product_id=product_id, scopes=scopes, **kwargs)
        return product.get_contract(contract_id).distributions

    def get_distribution(
        self,
        product_id: int,
        contract_id: int,
        distribution_id: int,
        *,
        scopes: list[Scope] | None = None,
        **kwargs,
    ) -> Distribution:
        product = self.get_product(product_id, scopes=scopes, **kwargs)
        return product.get_distribution(
            contract_id=contract_id,
            distribution_id=distribution_id,
        )

    @authorize.is_admin
    @authorize.is_team_member
    def create_distribution(
        self, *, product_id: int, contract_id: int, data: dict, **kwargs
    ) -> Distribution:
        product = self.get_product(product_id=product_id, **kwargs)
        refresh_period = data.pop("refresh_period", None)
        distribution = Distribution(
            **data,
            refresh_period=(RefreshPeriod.from_dict(refresh_period) if refresh_period else None),
        )
        product.add_distribution_to_contract(contract_id, distribution)

        updated_product = self._persist(product)
        return updated_product.get_contract(contract_id).distributions[-1]

    @authorize.is_admin
    @authorize.is_team_member
    def update_distribution(
        self, *, product_id: int, contract_id: int, distribution_id: int, data: dict, **kwargs
    ) -> Distribution:
        product = self.repository.get(product_id)
        distribution = product.update_distribution(contract_id, distribution_id, data)
        self._persist(product)
        return distribution

    @authorize.is_admin
    @authorize.is_team_member
    def delete_distribution(
        self, product_id: int, contract_id: int, distribution_id: int, **kwargs
    ) -> int:
        product = self.repository.get(product_id)
        product.delete_distribution(contract_id, distribution_id)
        self._persist(product)
        return distribution_id

    def get_services(
        self,
        product_id: int,
        *,
        scopes: list[Scope] | None = None,
        **kwargs,
    ) -> list[DataService]:
        product = self.get_product(product_id, scopes=scopes, **kwargs)
        return product.services

    def get_service(
        self,
        product_id: int,
        service_id: int,
        *,
        scopes: list[Scope] | None = None,
        **kwargs,
    ) -> DataService:
        product = self.get_product(product_id, scopes=scopes, **kwargs)
        return product.get_service(service_id)

    @authorize.is_admin
    @authorize.is_team_member
    def create_service(self, product_id: int, data: dict, **kwargs) -> DataService:
        product = self.get_product(product_id=product_id, **kwargs)
        product.create_service(data)
        updated_product = self._persist(product)
        return updated_product.services[-1]

    @authorize.is_admin
    @authorize.is_team_member
    def update_service(
        self, product_id: int, service_id: int, data: dict, **kwargs
    ) -> DataService:
        product = self.get_product(product_id=product_id, **kwargs)
        service = product.update_service(service_id, data)
        self._persist(product)
        return service

    @authorize.is_admin
    @authorize.is_team_member
    def delete_service(self, product_id: int, service_id: int, **kwargs) -> int:
        product = self.get_product(product_id=product_id, **kwargs)
        product.delete_service(service_id)
        self._persist(product)
        return service_id

    def _persist(self, product: Product) -> Product:
        return self.repository.save(product)
