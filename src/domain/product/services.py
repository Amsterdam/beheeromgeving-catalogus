import copy

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

    def _normalize_contract_draft_data(self, data: dict) -> dict:
        distributions = data.get("distributions")
        if distributions is None:
            return data

        normalized = dict(data)
        normalized["distributions"] = [
            Distribution(
                id=distribution.get("id"),
                access_service_id=distribution.get("access_service_id"),
                access_url=distribution.get("access_url"),
                download_url=distribution.get("download_url"),
                format=distribution.get("format"),
                filename=distribution.get("filename"),
                type=distribution.get("type"),
                refresh_period=(
                    RefreshPeriod.from_dict(distribution["refresh_period"])
                    if distribution.get("refresh_period")
                    else None
                ),
                crs=distribution.get("crs"),
            )
            for distribution in distributions
        ]
        return normalized

    @authorize.is_admin
    def get_all_products(self, **kwargs) -> list[Product]:
        return self.repository.list_all()

    def _get_exception(self, scopes: list[Scope] | None, message: str):
        if scopes:
            return exceptions.NotAuthorized(message)
        else:
            return exceptions.NotAuthenticated(message)

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

        try:
            return self.repository.get_for_publication_status(
                product_id,
                [enums.PublicationStatus.PUBLISHED],
            )
        except exceptions.AuthException as exc:
            raise self._get_exception(scopes, exc.message) from exc

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

        try:
            return self.repository.get_for_publication_status_by_name(
                name,
                [enums.PublicationStatus.PUBLISHED],
            )
        except exceptions.AuthException as exc:
            raise self._get_exception(scopes, exc.message) from exc

    @authorize.is_admin
    @authorize.is_team_member
    def create_product(self, *, data: dict, **kwargs) -> Product:
        refresh_period_data = data.pop("refresh_period", None)
        refresh_period = (
            RefreshPeriod.from_dict(refresh_period_data) if refresh_period_data else None
        )
        access_url = data.pop("access_url", None)

        product = Product(
            refresh_period=refresh_period,
            publication_status=enums.PublicationStatus.DRAFT,
            last_editor=kwargs.get("last_editor"),
            **data,
        )

        if product.type == enums.ProductType.INFORMATIEPRODUCT and access_url:
            # Also create a default contract and distribution for the access_url
            contract = DataContract(
                name=f"Contract voor {product.name}",
                publication_status=enums.PublicationStatus.DRAFT,
                distributions=[
                    Distribution(
                        access_url=access_url,
                        type=enums.DistributionType.REPORT,
                        refresh_period=refresh_period,
                    )
                ],
            )
            product.create_contract(contract)

        return self._persist(product)

    def _update_access_url_for_information_product(
        self, existing_product: Product, access_url: str, data: dict
    ):
        if not existing_product.contracts:
            contract = DataContract(
                name=f"Contract voor {existing_product.name}",
                publication_status=enums.PublicationStatus.DRAFT,
                distributions=[
                    Distribution(
                        access_url=access_url,
                        type=enums.DistributionType.REPORT,
                        refresh_period=data.get("refresh_period"),
                    )
                ],
            )
            existing_product.create_contract(contract)
        elif not existing_product.contracts[0].distributions:
            if not existing_product.contracts[0].id:
                raise exceptions.DomainException(
                    "Existing product has invalid contract data, cannot add distribution with "
                    "access_url"
                )
            existing_product.add_distribution_to_contract(
                contract_id=existing_product.contracts[0].id,
                distribution=Distribution(
                    access_url=access_url,
                    type=enums.DistributionType.REPORT,
                    refresh_period=data.get("refresh_period"),
                ),
            )
        else:
            if (
                not existing_product.contracts[0].id
                or not existing_product.contracts[0].distributions[0].id
            ):
                raise exceptions.DomainException(
                    "Existing product has invalid contract/distribution data, cannot update "
                    "access_url"
                )
            existing_product.update_distribution(
                contract_id=existing_product.contracts[0].id,
                distribution_id=existing_product.contracts[0].distributions[0].id,
                data={
                    "access_url": access_url,
                    "type": enums.DistributionType.REPORT,
                    "refresh_period": data.get("refresh_period"),
                },
            )
        return existing_product

    @authorize.is_admin
    @authorize.is_team_member
    def update_product(self, *, product_id: int, data: dict, **kwargs) -> Product:
        existing_product = self.get_product(product_id=product_id, **kwargs)
        access_url = data.pop("access_url", None) if "access_url" in data else None
        if data.get("refresh_period"):
            data["refresh_period"] = RefreshPeriod.from_dict(data["refresh_period"])
        if kwargs.get("last_editor"):
            data["last_editor"] = kwargs["last_editor"]
        existing_product.update(data)
        if existing_product.type == enums.ProductType.INFORMATIEPRODUCT and access_url:
            existing_product = self._update_access_url_for_information_product(
                existing_product=existing_product,
                access_url=access_url,
                data=data,
            )

        return self._persist(existing_product)

    @authorize.is_admin
    @authorize.is_team_member
    def get_product_draft(self, *, product_id: int, **kwargs) -> Product:
        product = self.repository.get(product_id)
        if product.publication_status != enums.PublicationStatus.PUBLISHED:
            raise exceptions.IllegalOperation(
                "Product working copies are only available for externally published products."
            )
        return self.repository.get_draft(product_id)

    @authorize.is_admin
    @authorize.is_team_member
    def update_product_draft(self, *, product_id: int, data: dict, **kwargs) -> Product:
        live_product = self.repository.get(product_id)
        if live_product.publication_status != enums.PublicationStatus.PUBLISHED:
            raise exceptions.IllegalOperation(
                "Product working copies are only available for externally published products."
            )
        if "access_url" in data:
            raise exceptions.IllegalOperation(
                "Cannot update access_url through a product working copy."
            )
        if data.get("refresh_period"):
            data["refresh_period"] = RefreshPeriod.from_dict(data["refresh_period"])
        if kwargs.get("last_editor"):
            data["last_editor"] = kwargs["last_editor"]

        try:
            draft_product = self.repository.get_draft(product_id)
        except exceptions.ObjectDoesNotExist:
            draft_product = copy.deepcopy(live_product)

        live_status = live_product.publication_status
        live_publication_date = live_product.publication_date
        draft_product.publication_status = enums.PublicationStatus.DRAFT
        draft_product.update(data)
        draft_product.publication_status = live_status
        draft_product.publication_date = live_publication_date
        return self.repository.save_draft(draft_product)

    @authorize.is_admin
    @authorize.is_team_member
    def discard_product_draft(self, *, product_id: int, **kwargs) -> int:
        product = self.repository.get(product_id)
        if product.publication_status != enums.PublicationStatus.PUBLISHED:
            raise exceptions.IllegalOperation(
                "Product working copies are only available for externally published products."
            )
        return self.repository.delete_draft(product_id)

    @authorize.is_admin
    @authorize.is_team_member
    def publish_product_draft(self, *, product_id: int, **kwargs) -> Product:
        product = self.repository.get(product_id)
        if product.publication_status != enums.PublicationStatus.PUBLISHED:
            raise exceptions.IllegalOperation(
                "Product working copies are only available for externally published products."
            )
        return self.repository.publish_draft(product_id)

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

    def _get_contract_for_working_copy(
        self,
        *,
        product_id: int,
        contract_id: int,
        scopes: list[Scope] | None = None,
        **kwargs,
    ) -> DataContract:
        product = self.get_product(product_id=product_id, scopes=scopes, **kwargs)
        contract = product.get_contract(contract_id)
        if (
            product.type != enums.ProductType.DATAPRODUCT
            or product.publication_status != enums.PublicationStatus.PUBLISHED
            or contract.publication_status != enums.PublicationStatus.PUBLISHED
        ):
            raise exceptions.IllegalOperation(
                "Contract working copies are only available for externally published "
                "dataproduct contracts."
            )
        return contract

    @authorize.is_admin
    @authorize.is_team_member
    def get_contract_draft(
        self,
        *,
        product_id: int,
        contract_id: int,
        scopes: list[Scope] | None = None,
        **kwargs,
    ) -> DataContract:
        self._get_contract_for_working_copy(
            product_id=product_id,
            contract_id=contract_id,
            scopes=scopes,
            **kwargs,
        )
        return self.repository.get_contract_draft(product_id=product_id, contract_id=contract_id)

    @authorize.is_admin
    @authorize.is_team_member
    def update_contract_draft(
        self,
        *,
        product_id: int,
        contract_id: int,
        data: dict,
        scopes: list[Scope] | None = None,
        **kwargs,
    ) -> DataContract:
        live_contract = self._get_contract_for_working_copy(
            product_id=product_id,
            contract_id=contract_id,
            scopes=scopes,
            **kwargs,
        )
        if kwargs.get("last_editor"):
            data["last_editor"] = kwargs["last_editor"]

        try:
            draft_contract = self.repository.get_contract_draft(
                product_id=product_id,
                contract_id=contract_id,
            )
        except exceptions.ObjectDoesNotExist:
            draft_contract = copy.deepcopy(live_contract)

        data = self._normalize_contract_draft_data(data)
        live_status = live_contract.publication_status
        live_publication_date = live_contract.publication_date
        draft_contract.publication_status = enums.PublicationStatus.DRAFT
        draft_contract.update_from_dict(data)
        draft_contract.publication_status = live_status
        draft_contract.publication_date = live_publication_date
        return self.repository.save_contract_draft(product_id=product_id, contract=draft_contract)

    @authorize.is_admin
    @authorize.is_team_member
    def discard_contract_draft(
        self,
        *,
        product_id: int,
        contract_id: int,
        scopes: list[Scope] | None = None,
        **kwargs,
    ) -> int:
        self._get_contract_for_working_copy(
            product_id=product_id,
            contract_id=contract_id,
            scopes=scopes,
            **kwargs,
        )
        return self.repository.delete_contract_draft(
            product_id=product_id, contract_id=contract_id
        )

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
