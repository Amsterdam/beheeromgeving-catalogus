from dataclasses import dataclass, field
from enum import StrEnum
from typing import NewType

from domain.exceptions import ValidationError


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
        elif not isinstance(self.allowed_fields, set):
            raise ValidationError("Permission has invalid allowed_fields.")
        return self.allowed_fields >= fields


class Rule:
    """A Rule definition for the authorization domain.

    decorator_name: The name of the decorator that will be added to the Authorizer
                    singleton instance.
    _method_name:   The name of the method name of the AuthorizationService if it differs
                    from the decorator_name.
    permission:     The applicable permission for this rule.
    role:           The applicable role for this rule.
    """

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


# Define standard rules.
RULES = [
    Rule(decorator_name="is_team_member"),
    Rule(
        decorator_name="can_update_team",
        method_name="permit",
        permission=Permission(
            role=Role.TEAM_MEMBER,
            allowed_fields={"po_name", "po_email", "contact_email"},
        ),
    ),
    Rule(decorator_name="is_admin", method_name="require", role=Role.ADMIN),
]


TeamId = NewType("TeamId", int)
ProductId = NewType("ProductId", int)
Scope = NewType("Scope", str)


class AuthorizationConfiguration:
    """This contains all configuration for the AuthorizationService, which originates either
    in the settings or the database.

    admin_role:     The role for the admin, from the settings.
    team_scopes:    A mapping from team_id to team scope.
    product_scopes: A mapping from product_id to team_scope.

    We have a feature flag in place, the feature_enabled flag determines whether it is on or not.
    """

    scopes_roles: dict[str, Role]
    scopes_team_id: dict[str, int]

    def __init__(
        self,
        admin_role: str,
        team_scopes: dict[TeamId, Scope],
        product_scopes: dict[ProductId | str, Scope],
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

    def team_id_to_scope(self, team_id: TeamId) -> Scope | AuthorizationResult:
        return self.team_scopes.get(team_id, AuthorizationResult.DENIED)

    def product_id_to_scope(self, product_id: ProductId) -> Scope | AuthorizationResult:
        return self.product_scopes.get(product_id, AuthorizationResult.DENIED)

    def product_name_to_scope(self, name: str) -> Scope | AuthorizationResult:
        return self.product_scopes.get(name, AuthorizationResult.DENIED)
