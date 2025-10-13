from django.db.utils import IntegrityError

from beheeromgeving import models as orm
from domain import exceptions
from domain.base import AbstractRepository
from domain.product import Product


class ProductRepository(AbstractRepository):
    _products: dict[int, Product]

    def __init__(self):
        self._products = {p.id: p.to_domain() for p in orm.Product.objects.all()}

    def get(self, product_id: int) -> Product:
        try:
            return self._products[product_id]
        except KeyError as e:
            raise exceptions.ObjectDoesNotExist from e

    def list(self, **kwargs) -> list[Product]:
        products = list(self._products.values())
        if kwargs.get("teams") is not None:
            team_ids = [team.id for team in kwargs["teams"]]
            products = [product for product in products if product.team_id in team_ids]
        return products

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
