from django.db.models import F, Manager, Value
from django.db.utils import IntegrityError

from beheeromgeving import models as orm
from domain import exceptions
from domain.base import AbstractRepository
from domain.product import Product
from domain.team import Team

# alias for typing
list_ = list


class ProductRepository(AbstractRepository[Product]):
    manager: Manager[orm.Product]

    def __init__(self):
        self.manager = orm.Product.objects.select_related("team").prefetch_related(
            "sources__pk", "team", "contracts", "contracts__distributions", "services"
        )

    def get(self, id: int) -> Product:
        try:
            return self.manager.get(pk=id).to_domain()
        except orm.Product.DoesNotExist as e:
            raise exceptions.ObjectDoesNotExist from e

    def get_published(self, id: int) -> Product:
        try:
            product = self.manager.get(pk=id).to_domain(published_only=True)
        except orm.Product.DoesNotExist as e:
            raise exceptions.ObjectDoesNotExist from e
        if product is None:
            raise exceptions.ObjectDoesNotExist
        return product

    def _get_by_name(self, name: str) -> orm.Product:
        product = (
            self.manager.annotate(search_name=Value(name))
            .filter(search_name__istartswith=F("name"))
            .first()
        )
        if not product:
            raise exceptions.ObjectDoesNotExist(f"Product with name {name} does not exist.")
        return product

    def get_by_name(self, name: str) -> Product:
        product = self._get_by_name(name)
        return product.to_domain()

    def get_published_by_name(self, name: str) -> Product:
        product = self._get_by_name(name).to_domain(published_only=True)
        if not product:
            raise exceptions.ObjectDoesNotExist(f"Product with name {name} does not exist.")
        return product

    def list_all(self, **kwargs):
        return [p.to_domain() for p in self.manager.all()]

    def list(
        self,
        *,
        query: str | None = None,
        filter: dict | None = None,
        exclude: dict | None = None,
        order: tuple[str, bool] | None = ("name", False),
    ) -> list_[Product]:
        products = self.manager.all()
        if filter:
            products = products.filter(**filter).distinct()
        if exclude:
            products = products.exclude(**exclude).distinct()
        if order:
            products = products.order_by(f"{'-' if order[1] else ''}{order[0]}")
        if query:
            products = {p.pk: p.to_domain(published_only=True) for p in products if p is not None}
            products = self.search(products, query)
        else:
            products = [p.to_domain(published_only=True) for p in products if p is not None]
        return products

    def list_mine(
        self,
        *,
        query: str | None = None,
        filter: dict | None = None,
        exclude: dict | None = None,
        order: tuple[str, bool] | None = ("name", False),
        teams: list_[Team],
    ) -> list_[Product]:
        team_ids = [team.id for team in teams]
        products = self.manager.filter(team_id__in=team_ids)
        if filter:
            products = products.filter(**filter).distinct()
        if exclude:
            products = products.exclude(**exclude).distinct()
        if order:
            products = products.order_by(f"{'-' if order[1] else ''}{order[0]}")
        if query:
            products = {p.pk: p.to_domain() for p in products}
            products = self.search(products, query)
        else:
            products = [p.to_domain() for p in products]
        return products

    def search(self, products: dict[int, Product], query: str) -> list_[Product]:
        query_words = query.lower().split(" ")
        # count how many occurences each word of the query are in the product's
        # search fields.
        results = {
            p_id: sum(1 for q in query_words if q in p.search_string)
            for p_id, p in products.items()
        }
        # sort them so the highest count appears first, and remove if count is 0.
        return [
            products[p_id]
            for p_id, count in sorted(results.items(), key=lambda item: item[1], reverse=True)
            if count > 0
        ]

    def save(self, item: Product) -> Product:
        try:
            return orm.Product.from_domain(item)
        except IntegrityError as e:
            raise exceptions.ValidationError(f"Error for {item.name}: {e!s}") from e

    def delete(self, id: int) -> int:
        num_delete, _ = orm.Product.objects.filter(pk=id).delete()
        if num_delete == 0:
            raise exceptions.ObjectDoesNotExist

        return id
