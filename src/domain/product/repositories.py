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
    ) -> list_[dict]:
        products = self.manager.all()
        if query:
            words = query.split()
            q_obj = Q()
            for word in words:
                q_obj |= (
                    Q(name__icontains=word)
                    | Q(description__icontains=word)
                    | Q(contracts__name__icontains=word)
                    | Q(contracts__description__icontains=word)
                )
            products = products.filter(q_obj).distinct()

            def count_occurrences(product: orm.Product) -> int:
                text = f"{product.name} {product.description} "
                text += " ".join([c.name + " " + c.description for c in product.contracts.all()])
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
        return [
            ProductList.from_django(p).model_dump()
            for p in products
            if p.publication_status == enums.PublicationStatus.PUBLISHED.value
        ]

    def list_mine(
        self,
        *,
        query: str | None = None,
        filter: dict | None = None,
        exclude: dict | None = None,
        order: tuple[str, bool] | None = ("name", False),
        teams: list_[Team],
    ) -> list_:
        team_ids = [team.id for team in teams]
        products = self.manager.filter(team_id__in=team_ids)
        if query:
            words = query.split()
            q_obj = Q()
            for word in words:
                q_obj |= (
                    Q(name__icontains=word)
                    | Q(description__icontains=word)
                    | Q(contracts__name__icontains=word)
                    | Q(contracts__description__icontains=word)
                )
            products = products.filter(q_obj).distinct()

            def count_occurrences(product: orm.Product) -> int:
                text = f"{product.name} {product.description} "
                text += " ".join([c.name + " " + c.description for c in product.contracts.all()])
                return sum(text.lower().count(word.lower()) for word in words)

        if filter:
            products = products.filter(**filter).distinct()
        if exclude:
            products = products.exclude(**exclude).distinct()
        if order:
            products = products.order_by(f"{'-' if order[1] else ''}{order[0]}")
        if query:
            products = sorted(products, key=lambda p: count_occurrences(p), reverse=True)

        return [MyProduct.from_django(p).model_dump() for p in products]

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
