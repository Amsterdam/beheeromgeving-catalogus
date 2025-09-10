from enum import StrEnum


class Role(StrEnum):
    ADMIN = "admin"
    TEAM_MEMBER = "team_member"


class AuthorizationConfiguration:
    mapping: list[Role]

    def __init__(self, admin_role: str, team_scopes: list[str]):
        self.mapping = dict.fromkeys(team_scopes, Role.TEAM_MEMBER)
        self.mapping[admin_role] = Role.ADMIN

    def scope_to_role(self, scope):
        return self.mapping.get(scope, None)
