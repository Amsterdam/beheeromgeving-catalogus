from django.conf import settings

from domain import exceptions
from domain.auth import AuthorizationResult
from domain.base import (
    AbstractAuthRepository,
    AbstractRepository,
    BaseObject,
)
from domain.product import Product
from domain.team import Team

# alias for typing
list_ = list


class DummyRepoItem(BaseObject):
    id: int
    name: str
    scope: str
    team_id: int


class DummyRepository(AbstractRepository):
    """DummyRepository for tests. This also uses a DummyAuthRepo to keep things in sync."""

    _items: dict[int, DummyRepoItem]

    def __init__(
        self,
        objects: list_[DummyRepoItem],
        auth_repo: type[AbstractAuthRepository] = AbstractAuthRepository,
    ):
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

    def get_for_publication_status(self, id, allowed_statuses):
        allowed = {getattr(status, "value", status) for status in allowed_statuses}
        obj = self.get(id)
        obj_status = getattr(obj, "publication_status", None)
        obj_status = getattr(obj_status, "value", obj_status)
        if obj_status not in allowed:
            raise exceptions.ObjectDoesNotExist
        if hasattr(obj, "contracts") and obj.contracts is not None:
            obj.contracts = [
                c
                for c in obj.contracts
                if getattr(
                    getattr(c, "publication_status", None),
                    "value",
                    getattr(c, "publication_status", None),
                )
                in allowed
            ]
        return obj

    def get_by_name(self, name):
        try:
            normalized_name = name.replace("_", " ").lower()
            return next(
                item
                for item in self._items.values()
                if normalized_name.startswith(item.name.lower())
            )
        except StopIteration as e:
            raise exceptions.ObjectDoesNotExist(f"Object with name {name} does not exist") from e

    def get_for_publication_status_by_name(self, name, allowed_statuses):
        allowed = {getattr(status, "value", status) for status in allowed_statuses}
        obj = self.get_by_name(name)
        obj_status = getattr(obj, "publication_status", None)
        obj_status = getattr(obj_status, "value", obj_status)
        if obj_status not in allowed:
            raise exceptions.ObjectDoesNotExist
        if hasattr(obj, "contracts") and obj.contracts is not None:
            obj.contracts = [
                c
                for c in obj.contracts
                if getattr(
                    getattr(c, "publication_status", None),
                    "value",
                    getattr(c, "publication_status", None),
                )
                in allowed
            ]
        return obj

    def list_all(self, **_kwargs):
        return list(self._items.values())

    def list_for_publication_status(self, allowed_statuses, **_kwargs):
        allowed = {getattr(status, "value", status) for status in allowed_statuses}
        return [
            item
            for item in self._items.values()
            if getattr(
                getattr(item, "publication_status", None),
                "value",
                getattr(item, "publication_status", None),
            )
            in allowed
        ]

    def list(self):
        return list(self._items.values())

    def save(self, item: DummyRepoItem):
        self._add_ids(item)
        self._items[item.id] = item
        self.auth_repo.add_object(item)  # ty:ignore[unresolved-attribute]
        return item

    def delete(self, id):
        try:
            self._items.pop(id)
        except KeyError as e:
            raise exceptions.ObjectDoesNotExist(f"Object with id {id} does not exist") from e


class DummyAuthRepo(AbstractAuthRepository):
    def __init__(self, teams: list[DummyRepoItem], products: list[DummyRepoItem]):
        self.team_scopes = {}
        self.product_scopes = {}
        for team in teams:
            self.team_scopes[team.id] = team.scope
        for product in products:
            team_scope = self.team_scopes.get(product.team_id)
            self.product_scopes[product.id] = team_scope
            if getattr(product, "name", None):
                self.product_scopes[product.name.lower()] = team_scope

        self.feature_enabled = getattr(settings, "FEATURE_FLAG_USE_AUTH", True)
        self.admin_role = settings.ADMIN_ROLE_NAME
        self.employee_role = settings.EMPLOYEE_ROLE_NAME

    def add_object(self, object: Team | Product):
        if isinstance(object, Team):
            self.team_scopes[object.id] = object.scope
        elif isinstance(object, Product):
            team_scope = self.team_scopes.get(object.team_id)
            self.product_scopes[object.id] = team_scope
            if object.name:
                self.product_scopes[object.name.lower()] = team_scope

    def get_team_scope(self, team_id: int):
        return self.team_scopes.get(team_id, AuthorizationResult.DENIED)

    def get_product_scope(self, product_id: int):
        return self.product_scopes.get(product_id, AuthorizationResult.DENIED)

    def get_product_scope_by_name(self, name: str):
        return self.product_scopes.get(name.lower(), AuthorizationResult.DENIED)

    def can_access_team(self, team_id: int, scopes) -> bool:
        team_scope = self.get_team_scope(team_id)
        return team_scope in scopes

    def can_access_product(self, product_id: int, scopes) -> bool:
        product_scope = self.get_product_scope(product_id)
        return product_scope in scopes

    def can_access_product_name(self, name: str, scopes) -> bool:
        product_scope = self.get_product_scope_by_name(name)
        return product_scope in scopes
