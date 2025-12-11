from django.db.utils import IntegrityError

from beheeromgeving import models as orm
from domain import exceptions
from domain.base import AbstractRepository
from domain.product import Product

# alias for typing
list_ = list


class ProductRepository(AbstractRepository):
    _products: dict[int, Product]

    def __init__(self):
        self.refresh_from_db()

    def refresh_from_db(self):
        self._products = {p.id: p.to_domain() for p in orm.Product.objects.all()}

    def get(self, product_id: int) -> Product:
        try:
            return self._products[product_id]
        except KeyError as e:
            raise exceptions.ObjectDoesNotExist from e

    def get_by_name(self, name: str) -> Product:
        try:
            normalized_name = name.replace("_", " ").lower()
            return next(
                product
                for product in self._products.values()
                if normalized_name.startswith(product.name.lower())
            )
        except StopIteration as e:
            raise exceptions.ObjectDoesNotExist(f"Product with name {name} does not exist.") from e

    def list(
        self, *, query: str | None = None, filter: dict | None = None, **kwargs
    ) -> list_[Product]:
        products = self.search(query) if query is not None else list_(self._products.values())

        if filter:
            products = self.filter(products, filter)

        if kwargs.get("teams") is not None:
            team_ids = [team.id for team in kwargs["teams"]]
            products = [product for product in products if product.team_id in team_ids]
        return products

    def search(self, query: str) -> list_[Product]:
        query_words = query.lower().split(" ")
        # count how many occurences each word of the query are in the product's
        # search fields.
        results = {
            p_id: sum(1 for q in query_words if q in p.search_string)
            for p_id, p in self._products.items()
        }
        # sort them so the highest count appears first, and remove if count is 0.
        return [
            self._products[p_id]
            for p_id, count in sorted(results.items(), key=lambda item: item[1], reverse=True)
            if count > 0
        ]

    def filter(self, products: list_[Product], filter: dict) -> list_[Product]:
        return [product for product in products if product.matches_filter(filter)]

    def save(self, product: Product) -> Product:
        try:
            saved_product = orm.Product.from_domain(product)
        except IntegrityError as e:
            raise exceptions.ValidationError(f"Error for {product.name}: {e!s}") from e
        self._products[saved_product.id] = saved_product
        return saved_product

    def delete(self, product_id: int) -> int:
        try:
            self._products.pop(product_id)
        except KeyError as e:
            raise exceptions.ObjectDoesNotExist from e

        orm.Product.objects.filter(id=product_id).delete()
        return product_id
