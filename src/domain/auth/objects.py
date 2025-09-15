from dataclasses import dataclass, field
from enum import StrEnum
from typing import NewType


class AuthorizationResult(StrEnum):
    GRANTED = "granted"
    DENIED = "denied"


class Role(StrEnum):
    ADMIN = "admin"
    TEAM_MEMBER = "team_member"
    ANONYMOUS = "anonymous"


@dataclass
class Permission:
    """Which fields are allowed to access by which role."""

    ALL = "__all__"
    role: Role
    allowed_fields: set[str] | str = field(default_factory=set)

    def can_access_fields(self, fields: set[str]):
        if self.allowed_fields == self.ALL:
            return True
        return self.allowed_fields >= fields


class Rule:
    decorator_name: str
    _method_name: str | None = None
    permission: Permission | None = None
    role: Role | None = None

    def __init__(
        self,
        decorator_name: str,
        method_name: str | None = None,
        permission: Permission | None = None,
        role: Role | None = None,
    ):
        self.decorator_name = decorator_name
        self._method_name = method_name
        self.permission = permission
        self.role = role

    @property
    def method_name(self):
        return self._method_name or self.decorator_name

    @method_name.setter
    def method_name(self, name):
        self._method_name = name


RULES = [
    Rule(decorator_name="is_team_member"),
    Rule(
        decorator_name="can_update_team",
        method_name="permit",
        permission=Permission(
            role=Role.TEAM_MEMBER, allowed_fields={"po_name", "po_email", "contact_email"}
        ),
    ),
    Rule(decorator_name="is_admin", method_name="require", role=Role.ADMIN),
]


TeamId = NewType("TeamId", int)
ProductId = NewType("ProductId", int)
Scope = NewType("Scope", str)


class AuthorizationConfiguration:
    scopes_roles: dict[str, Role]
    scopes_team_id: dict[str, int]

    def __init__(
        self,
        admin_role: Scope,
        team_scopes: dict[TeamId, Scope],
        product_scopes: dict[ProductId, Scope],
        feature_enabled: bool = True,
    ):
        self.team_scopes = team_scopes or {}
        self.product_scopes = product_scopes or {}
        self.admin_role = admin_role
        self.feature_enabled = feature_enabled

    def scope_to_role(self, scope: Scope) -> Role | None:
        if scope == self.admin_role:
            return Role.ADMIN
        if scope in self.team_scopes.values():
            return Role.TEAM_MEMBER
        return None

    def team_id_to_scope(self, team_id: TeamId) -> Scope | None:
        return self.team_scopes.get(team_id, AuthorizationResult.DENIED)

    def product_id_to_scope(self, product_id: ProductId) -> Scope | None:
        return self.product_scopes.get(product_id, AuthorizationResult.DENIED)
