from dataclasses import dataclass, field
from enum import StrEnum


class Role(StrEnum):
    ADMIN = "admin"
    TEAM_MEMBER = "team_member"
    ANONYMOUS = "anonymous"


@dataclass
class Permissions:
    all = "__all__"
    admin: set[str] | str = field(default_factory=set)
    team_member: set[str] | str = field(default_factory=set)
    anonymous: set[str] | str = field(default_factory=set)

    def can_access_fields(self, roles: set[Role], fields: set[str]):
        for role in roles:
            allowed_fields = getattr(self, role.value)
            if allowed_fields == self.all:
                return True
            if not fields - allowed_fields:
                return True
            continue
        return False


class AuthorizationConfiguration:
    mapping: list[Role]

    def __init__(self, admin_role: str, team_scopes: list[str]):
        self.mapping = dict.fromkeys(team_scopes, Role.TEAM_MEMBER)
        self.mapping[admin_role] = Role.ADMIN

    def scope_to_role(self, scope):
        return self.mapping.get(scope, None)
