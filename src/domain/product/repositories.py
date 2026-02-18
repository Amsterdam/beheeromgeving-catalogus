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
        self.manager = orm.Product.objects

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
        order: tuple[str, bool] | None = ("name", False),
    ) -> list_[Product]:
        if query:
            products = {p.pk: p.to_domain(published_only=True) for p in self.manager.all()}
            products = self.search(products, query)
        else:
            products = [p.to_domain(published_only=True) for p in self.manager.all()]
        products = [p for p in products if p is not None]
        if filter:
            products = self.filter(products, filter)
        if order:
            products = self.order(products, order)
        return products

    def list_mine(
        self,
        *,
        query: str | None = None,
        filter: dict | None = None,
        order: tuple[str, bool] | None = ("name", False),
        teams: list_[Team],
    ) -> list_[Product]:
        if query:
            products = {p.pk: p.to_domain() for p in self.manager.all()}
            products = self.search(products, query)
        else:
            products = [p.to_domain() for p in self.manager.all()]
        if filter:
            products = self.filter(products, filter)
        if order:
            products = self.order(products, order)
        team_ids = [team.id for team in teams]
        return [product for product in products if product.team_id in team_ids]

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

    def order(self, products: list_[Product], order: tuple[str, bool]) -> list_[Product]:
        order_field, reversed = order

        def lookup(product):
            return getattr(product, order_field)

        return sorted(products, key=lookup, reverse=reversed)

    def filter(self, products: list_[Product], filter: dict) -> list_[Product]:
        return [product for product in products if product.matches_filter(filter)]

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
