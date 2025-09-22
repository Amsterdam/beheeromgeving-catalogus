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

    def _add_ids(self, object):
        """Ensure the object we save to the repository has id for itself and all its
        underlying subobjects."""
        object.id = object.id or max(self._items.keys()) + 1 if len(self._items.keys()) else 0
        if hasattr(object, "contracts") and object.contracts is not None:
            new_contract_id = max([c.id for c in object.contracts if c.id] or [0]) + 1
            for contract in object.contracts:
                if contract.id is None:
                    contract.id = new_contract_id
                    new_contract_id += 1

                if hasattr(contract, "distributions") and contract.distributions is not None:
                    new_distro_id = max([d.id for d in contract.distributions if d.id] or [0]) + 1
                    for distro in contract.distributions:
                        if distro.id is None:
                            distro.id = new_distro_id
                            new_distro_id += 1
        if hasattr(object, "services") and object.services is not None:
            new_service_id = max([s.id for s in object.services if s.id] or [0]) + 1
            for service in object.services:
                if service.id is None:
                    service.id = new_service_id
                    new_service_id += 1

    def get(self, id):
        try:
            return self._items[id]
        except KeyError as e:
            raise exceptions.ObjectDoesNotExist(f"Object with id {id} does not exist") from e

    def list(self):
        return list(self._items.values())

    def save(self, object: BaseObject):
        self._add_ids(object)
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
