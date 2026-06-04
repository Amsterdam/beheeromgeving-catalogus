from django.db import transaction
from django.db.models import F, Q, QuerySet, Value
from django.db.utils import IntegrityError

from api.datatransferobjects import MyProduct, ProductList
from beheeromgeving import models as orm
from domain import exceptions
from domain.base import AbstractRepository
from domain.product import Product, enums
from domain.team import Team

# alias for typing
list_ = list


class ProductRepository(AbstractRepository[Product]):
    manager: QuerySet[orm.Product]

    def __init__(self):
        self.manager = orm.Product.objects.select_related("team").prefetch_related(
            "sources__pk", "team", "contracts", "contracts__distributions", "services"
        )
        self.draft_manager = orm.ProductWorkingCopy.objects.select_related(
            "product", "product__team", "team"
        ).prefetch_related(
            "product__sources__pk",
            "product__team",
            "product__contracts",
            "product__contracts__distributions",
            "product__services",
        )

    def get(self, id: int) -> Product:
        try:
            return self.manager.get(pk=id).to_domain()
        except orm.Product.DoesNotExist as e:
            raise exceptions.ObjectDoesNotExist from e

    def get_for_publication_status(
        self, id: int, allowed_statuses: list_[enums.PublicationStatus]
    ) -> Product:
        allowed = {status.value for status in allowed_statuses}
        try:
            product = self.manager.get(pk=id)
        except orm.Product.DoesNotExist as e:
            raise exceptions.ObjectDoesNotExist from e

        if product.publication_status not in allowed:
            raise exceptions.AuthException(f"Not authorized to access product with id {id}.")

        domain_product = product.to_domain()
        domain_product.contracts = [
            contract
            for contract in domain_product.contracts
            if contract.publication_status in allowed
        ]
        return domain_product

    def _get_by_name(self, name: str) -> orm.Product:
        product = (
            self.manager.annotate(search_name=Value(name))
            .filter(search_name__iexact=F("name"))
            .first()
        )
        if not product:
            raise exceptions.ObjectDoesNotExist(f"Product with name {name} does not exist.")
        return product

    def get_by_name(self, name: str) -> Product:
        product = self._get_by_name(name)
        return product.to_domain()

    def get_for_publication_status_by_name(
        self, name: str, allowed_statuses: list_[enums.PublicationStatus]
    ) -> Product:
        allowed = {status.value for status in allowed_statuses}
        product = self._get_by_name(name)
        if product.publication_status not in allowed:
            raise exceptions.AuthException(f"Not authorized to access product with name {name}.")
        domain_product = product.to_domain()
        domain_product.contracts = [
            contract
            for contract in domain_product.contracts
            if contract.publication_status in allowed
        ]
        return domain_product

    def list_all(self, **kwargs):
        return [p.to_domain() for p in self.manager.all()]

    def list_for_publication_status(
        self,
        allowed_statuses: list_[enums.PublicationStatus],
        *,
        query: str | None = None,
        filter: dict | None = None,
        exclude: dict | None = None,
        order: tuple[str, bool] | None = ("name", False),
        fields: list[str] | None = None,
    ) -> list_[dict]:
        allowed = {status.value for status in allowed_statuses}
        products = self.manager.filter(publication_status__in=allowed)

        if filter is not None:
            filter = {**filter}
            filter.pop("publication_status", None)

        products = self._apply_filters(
            products,
            query=query,
            filter=filter,
            exclude=exclude,
            order=order,
        )
        dump_kwargs = {}
        if fields not in (None, "*"):
            dump_kwargs["include"] = fields
        return [ProductList.from_django(p).model_dump(**dump_kwargs) for p in products]

    def _apply_filters(
        self,
        products,
        *,
        query: str | None = None,
        filter: dict | None = None,
        exclude: dict | None = None,
        order: tuple[str, bool] | None = ("name", False),
    ):
        if query:
            words = query.split()
            q_obj = Q()
            for word in words:
                q_obj |= (
                    Q(name__icontains=word)
                    | Q(description__icontains=word)
                    | Q(contracts__name__icontains=word)
                )
            products = products.filter(q_obj).distinct()

            def count_occurrences(product: orm.Product) -> int:
                text = f"{product.name} {product.description} "
                text += " ".join([(c.name or "") for c in product.contracts.all()])
                text_lower = text.lower()
                return sum(1 if word.lower() in text_lower else 0 for word in words)

        if filter:
            products = products.filter(**filter).distinct()
        if exclude:
            products = products.exclude(**exclude).distinct()
        if order:
            products = products.order_by(f"{'-' if order[1] else ''}{order[0]}")
        # If query was used, sort by occurrence count
        if query:
            products = sorted(products, key=lambda p: count_occurrences(p), reverse=True)
        return products

    def list_mine(
        self,
        *,
        query: str | None = None,
        filter: dict | None = None,
        exclude: dict | None = None,
        order: tuple[str, bool] | None = ("name", False),
        fields: list[str] | None = None,
        teams: list_[Team],
    ) -> list_:
        team_ids = [team.id for team in teams]
        products = self.manager.filter(team_id__in=team_ids)
        products = self._apply_filters(
            products,
            query=query,
            filter=filter,
            exclude=exclude,
            order=order,
        )
        dump_kwargs = {}
        if fields not in (None, "*"):
            dump_kwargs["include"] = fields
        return [MyProduct.from_django(p).model_dump(**dump_kwargs) for p in products]

    def save(self, item: Product) -> Product:
        try:
            return orm.Product.from_domain(item)
        except IntegrityError as e:
            raise exceptions.ValidationError(f"Error for {item.name}: {e!s}") from e

    def get_draft(self, id: int) -> Product:
        try:
            return self.draft_manager.get(product_id=id).to_domain()
        except orm.ProductWorkingCopy.DoesNotExist as e:
            raise exceptions.ObjectDoesNotExist(
                f"Product working copy for product with id {id} does not exist."
            ) from e

    def save_draft(self, item: Product) -> Product:
        try:
            return orm.ProductWorkingCopy.from_domain(item)
        except orm.Product.DoesNotExist as e:
            raise exceptions.ObjectDoesNotExist from e
        except IntegrityError as e:
            raise exceptions.ValidationError(f"Error for {item.name}: {e!s}") from e

    def publish_draft(self, id: int) -> Product:
        try:
            with transaction.atomic():
                live_product = orm.Product.objects.select_for_update().get(pk=id)
                draft = (
                    orm.ProductWorkingCopy.objects.select_related("product", "team")
                    .select_for_update()
                    .get(product_id=id)
                )

                if live_product.last_updated != draft.base_last_updated:
                    raise exceptions.IllegalOperation(
                        "Cannot publish product working copy because the live product has changed."
                    )

                published_product = self.save(draft.to_domain())
                draft.delete()
                return published_product
        except orm.Product.DoesNotExist as e:
            raise exceptions.ObjectDoesNotExist from e
        except orm.ProductWorkingCopy.DoesNotExist as e:
            raise exceptions.ObjectDoesNotExist(
                f"Product working copy for product with id {id} does not exist."
            ) from e

    def delete_draft(self, id: int) -> int:
        num_delete, _ = orm.ProductWorkingCopy.objects.filter(product_id=id).delete()
        if num_delete == 0:
            raise exceptions.ObjectDoesNotExist(
                f"Product working copy for product with id {id} does not exist."
            )

        return id

    def delete(self, id: int) -> int:
        num_delete, _ = orm.Product.objects.filter(pk=id).delete()
        if num_delete == 0:
            raise exceptions.ObjectDoesNotExist

        return id
