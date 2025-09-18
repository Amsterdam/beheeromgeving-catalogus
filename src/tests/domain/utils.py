from django.conf import settings

from domain import exceptions
from domain.auth import AuthorizationConfiguration
from domain.base import AbstractAuthRepository, AbstractRepository, BaseObject
from domain.product import Product
from domain.team import Team


class DummyRepository(AbstractRepository):
    """DummyRepository for tests. This also uses a DummyAuthRepo to keep things in sync."""

    _items: dict[int, BaseObject]

    def __init__(self, objects: list[BaseObject], auth_repo=AbstractAuthRepository):
        self._items = {}
        self.auth_repo = auth_repo
        for object in objects:
            self._items[object.id] = object

    def get(self, id):
        try:
            return self._items[id]
        except KeyError as e:
            raise exceptions.ObjectDoesNotExist(f"Object with id {id} does not exist") from e

    def list(self):
        return list(self._items.values())

    def save(self, object: BaseObject):
        object.id = object.id or max(self._items.keys()) + 1 if len(self._items.keys()) else 0
        self._items[object.id] = object
        self.auth_repo.add_object(object)
        return object

    def delete(self, id):
        try:
            self._items.pop(id)
        except KeyError as e:
            raise exceptions.ObjectDoesNotExist(f"Object with id {id} does not exist") from e


class DummyAuthRepo(AbstractAuthRepository):
    def __init__(self, teams: list[BaseObject], products: list[BaseObject]):
        self.team_scopes = {}
        self.product_scopes = {}
        for team in teams:
            self.team_scopes[team.id] = team.scope
        for product in products:
            self.product_scopes[product.id] = self.team_scopes.get(product.team_id)

    def add_object(self, object: Team | Product):
        if isinstance(object, Team):
            self.team_scopes[object.id] = object.scope
        elif isinstance(object, Product):
            self.product_scopes[object.id] = self.team_scopes.get(object.team_id)

    def get_config(self):
        return AuthorizationConfiguration(
            settings.ADMIN_ROLE_NAME, self.team_scopes, self.product_scopes
        )
