from dataclasses import dataclass, field
from enum import StrEnum
from typing import NewType

GRANTED = "OK"
DENIED = "NOPE"


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


TeamId = NewType("TeamId", int)
ProductId = NewType("ProductId", int)
Scope = NewType("Scope", str)


class AuthorizationConfiguration:
    scopes_roles: dict[str, Role]
    scopes_team_id: dict[str, int]

    def __init__(
        self,
        admin_role: str,
        team_scopes: dict[TeamId, Scope],
        product_scopes: dict[ProductId, Scope],
    ):
        self.team_scopes = team_scopes or {}
        self.product_scopes = product_scopes or {}
        self.admin_role = admin_role

    def scope_to_role(self, scope: Scope) -> Role | None:
        if scope == self.admin_role:
            return Role.ADMIN
        if scope in self.team_scopes.values():
            return Role.TEAM_MEMBER
        return None

    def team_id_to_scope(self, team_id: TeamId) -> Scope | None:
        print(self.team_scopes)
        return self.team_scopes.get(team_id, DENIED)

    def product_id_to_scope(self, product_id: ProductId) -> Scope | None:
        return self.product_scopes.get(product_id, DENIED)
