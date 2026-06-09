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
    def get_product_revision(self, *, product_id: int, **kwargs) -> Product:
        product = self.repository.get(product_id)
        if product.publication_status != enums.PublicationStatus.PUBLISHED:
            raise exceptions.IllegalOperation(
                "Product working copies are only available for externally published products."
            )
        return self.repository.get_revision(product_id)

    @authorize.is_admin
    @authorize.is_team_member
    def update_product_revision(self, *, product_id: int, data: dict, **kwargs) -> Product:
        live_product = self.repository.get(product_id)
        if live_product.publication_status != enums.PublicationStatus.PUBLISHED:
            raise exceptions.IllegalOperation(
                "Product working copies are only available for externally published products."
            )
        if "access_url" in data:
            raise exceptions.IllegalOperation(
                "Cannot update access_url through a product revision."
            )
        if data.get("refresh_period"):
            data["refresh_period"] = RefreshPeriod.from_dict(data["refresh_period"])
        if kwargs.get("last_editor"):
            data["last_editor"] = kwargs["last_editor"]

        try:
            revision_product = self.repository.get_revision(product_id)
        except exceptions.ObjectDoesNotExist:
            revision_product = copy.deepcopy(live_product)

        revision_product.publication_status = enums.PublicationStatus.DRAFT
        revision_product.update(data)
        revision_product.publication_status = live_product.publication_status
        revision_product.publication_date = live_product.publication_date
        return self.repository.save_revision(revision_product)

    @authorize.is_admin
    @authorize.is_team_member
    def discard_product_revision(self, *, product_id: int, **kwargs) -> int:
        product = self.repository.get(product_id)
        if product.publication_status != enums.PublicationStatus.PUBLISHED:
            raise exceptions.IllegalOperation(
                "Product working copies are only available for externally published products."
            )
        return self.repository.delete_revision(product_id)

    @authorize.is_admin
    @authorize.is_team_member
    def publish_product_revision(self, *, product_id: int, **kwargs) -> Product:
        product = self.repository.get(product_id)
        if product.publication_status != enums.PublicationStatus.PUBLISHED:
            raise exceptions.IllegalOperation(
                "Product working copies are only available for externally published products."
            )
        return self.repository.publish_revision(product_id)

    def _delete_product_revision_if_exists(self, *, product_id: int) -> None:
        try:
            self.repository.delete_revision(product_id)
        except exceptions.ObjectDoesNotExist:
            pass

    def _delete_contract_revision_if_exists(self, *, product_id: int, contract_id: int) -> None:
        try:
            self.repository.delete_contract_revision(
                product_id=product_id,
                contract_id=contract_id,
            )
        except exceptions.ObjectDoesNotExist:
            pass

    @authorize.is_admin
    @authorize.is_team_member
    def delete_product(self, *, product_id: int, **kwargs) -> None:
        product = self.get_product(product_id=product_id, **kwargs)
        if product.publication_date is not None:
            published_contract_ids = [
                contract.id
                for contract in product.contracts
                if contract.id is not None and contract.publication_date is not None
            ]
            product.update_state({"publication_status": enums.PublicationStatus.DELETED})
            for contract in product.contracts:
                if contract.id:
                    product.delete_contract(contract.id)
            self._persist(product)
            self._delete_product_revision_if_exists(product_id=product_id)
            for contract_id in published_contract_ids:
                self._delete_contract_revision_if_exists(
                    product_id=product_id,
                    contract_id=contract_id,
                )
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

    def _get_contract_for_revision(
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
                "Contract revisions are only available for externally published "
                "dataproduct contracts."
            )
        return contract

    def _get_product_for_contract_live_mutation(
        self,
        *,
        product_id: int,
        contract_id: int,
        scopes: list[Scope] | None = None,
        **kwargs,
    ) -> Product:
        product = self.get_product(product_id=product_id, scopes=scopes, **kwargs)
        contract = product.get_contract(contract_id)
        if (
            product.type == enums.ProductType.DATAPRODUCT
            and product.publication_status == enums.PublicationStatus.PUBLISHED
            and contract.publication_status == enums.PublicationStatus.PUBLISHED
        ):
            raise exceptions.IllegalOperation(
                "Published dataproduct contracts must be edited through the contract "
                "revision flow."
            )
        return product

    def _validate_contract_revision_service_references(
        self,
        *,
        product: Product,
        contract: DataContract,
    ) -> None:
        published_service_ids = {
            service.id for service in product.services if service.id is not None
        }
        invalid_service_ids = sorted(
            {
                distribution.access_service_id
                for distribution in contract.distributions
                if distribution.access_service_id is not None
                and distribution.access_service_id not in published_service_ids
            }
        )
        if invalid_service_ids:
            raise exceptions.ValidationError(
                "Cannot publish contract revision because distributions must "
                "reference the published service set."
            )

    @authorize.is_admin
    @authorize.is_team_member
    def get_contract_revision(
        self,
        *,
        product_id: int,
        contract_id: int,
        scopes: list[Scope] | None = None,
        **kwargs,
    ) -> DataContract:
        self._get_contract_for_revision(
            product_id=product_id,
            contract_id=contract_id,
            scopes=scopes,
            **kwargs,
        )
        return self.repository.get_contract_revision(
            product_id=product_id,
            contract_id=contract_id,
        )

    @authorize.is_admin
    @authorize.is_team_member
    def update_contract_revision(
        self,
        *,
        product_id: int,
        contract_id: int,
        data: dict,
        scopes: list[Scope] | None = None,
        **kwargs,
    ) -> DataContract:
        live_contract = self._get_contract_for_revision(
            product_id=product_id,
            contract_id=contract_id,
            scopes=scopes,
            **kwargs,
        )
        if kwargs.get("last_editor"):
            data["last_editor"] = kwargs["last_editor"]

        try:
            revision_contract = self.repository.get_contract_revision(
                product_id=product_id,
                contract_id=contract_id,
            )
        except exceptions.ObjectDoesNotExist:
            revision_contract = copy.deepcopy(live_contract)

        data = self._normalize_contract_draft_data(data)
        revision_contract.publication_status = enums.PublicationStatus.DRAFT
        revision_contract.update_from_dict(data)
        revision_contract.publication_status = live_contract.publication_status
        revision_contract.publication_date = live_contract.publication_date
        return self.repository.save_contract_revision(
            product_id=product_id,
            contract=revision_contract,
        )

    @authorize.is_admin
    @authorize.is_team_member
    def discard_contract_revision(
        self,
        *,
        product_id: int,
        contract_id: int,
        scopes: list[Scope] | None = None,
        **kwargs,
    ) -> int:
        self._get_contract_for_revision(
            product_id=product_id,
            contract_id=contract_id,
            scopes=scopes,
            **kwargs,
        )
        return self.repository.delete_contract_revision(
            product_id=product_id, contract_id=contract_id
        )

    @authorize.is_admin
    @authorize.is_team_member
    def publish_contract_revision(
        self,
        *,
        product_id: int,
        contract_id: int,
        scopes: list[Scope] | None = None,
        **kwargs,
    ) -> DataContract:
        self._get_contract_for_revision(
            product_id=product_id,
            contract_id=contract_id,
            scopes=scopes,
            **kwargs,
        )
        product = self.get_product(product_id=product_id, scopes=scopes, **kwargs)
        revision_contract = self.repository.get_contract_revision(
            product_id=product_id,
            contract_id=contract_id,
        )
        self._validate_contract_revision_service_references(
            product=product,
            contract=revision_contract,
        )
        return self.repository.publish_contract_revision(
            product_id=product_id,
            contract_id=contract_id,
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
        product = self._get_product_for_contract_live_mutation(
            product_id=product_id,
            contract_id=contract_id,
            **kwargs,
        )
        if kwargs.get("last_editor"):
            data["last_editor"] = kwargs["last_editor"]
        product.update_contract(contract_id, data)
        updated_product = self._persist(product)
        return updated_product.get_contract(contract_id)

    @authorize.is_admin
    @authorize.is_team_member
    def update_contract_publication_status(
        self, product_id: int, contract_id: int, data: dict, **kwargs
    ) -> DataContract:
        product = self.get_product(product_id=product_id, **kwargs)
        product.update_contract_state(contract_id, data)
        updated_product = self._persist(product)
        updated_contract = updated_product.get_contract(contract_id)
        if updated_contract.publication_status == enums.PublicationStatus.DELETED:
            self._delete_contract_revision_if_exists(
                product_id=product_id,
                contract_id=contract_id,
            )
        return updated_contract

    @authorize.is_admin
    @authorize.is_team_member
    def delete_contract(self, product_id: int, contract_id: int, **kwargs):
        product = self.get_product(product_id=product_id, **kwargs)
        contract = product.get_contract(contract_id)
        product.delete_contract(contract_id)
        self._persist(product)
        if contract.publication_date is not None:
            self._delete_contract_revision_if_exists(
                product_id=product_id,
                contract_id=contract_id,
            )

    @authorize.is_admin
    @authorize.is_team_member
    def update_publication_status(self, product_id: int, data: dict, **kwargs) -> Product:
        existing_product = self.repository.get(product_id)
        existing_product.update_state(data)
        updated_product = self._persist(existing_product)
        if updated_product.publication_status == enums.PublicationStatus.DELETED:
            self._delete_product_revision_if_exists(product_id=product_id)
        return updated_product

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
        product = self._get_product_for_contract_live_mutation(
            product_id=product_id,
            contract_id=contract_id,
            **kwargs,
        )
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
        product = self._get_product_for_contract_live_mutation(
            product_id=product_id,
            contract_id=contract_id,
            **kwargs,
        )
        distribution = product.update_distribution(contract_id, distribution_id, data)
        self._persist(product)
        return distribution

    @authorize.is_admin
    @authorize.is_team_member
    def delete_distribution(
        self, product_id: int, contract_id: int, distribution_id: int, **kwargs
    ) -> int:
        product = self._get_product_for_contract_live_mutation(
            product_id=product_id,
            contract_id=contract_id,
            **kwargs,
        )
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
