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
    EMPLOYEE = "employee"


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
    Rule(decorator_name="is_employee", method_name="require", role=Role.EMPLOYEE),
]


TeamId = NewType("TeamId", int)
ProductId = NewType("ProductId", int)
Scope = NewType("Scope", str)
