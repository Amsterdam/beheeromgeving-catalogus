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
        return list(self._products.values())

    def save(self, product: Product) -> Product:
        saved_product = orm.Product.from_domain(product)
        self._products[saved_product.id] = saved_product
        return saved_product

    def delete(self, product_id: int) -> int:
        try:
            self._products.pop(product_id)
        except KeyError as e:
            raise exceptions.ObjectDoesNotExist from e

        orm.Product.objects.filter(id=product_id).delete()
        return product_id
