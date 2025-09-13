from domain.auth import DENIED, GRANTED, AuthorizationConfiguration, Permission, Role
from domain.base import AbstractRepository
from domain.exceptions import DomainException, NotAuthorized


class AuthorizationService:

    def __init__(self, repo: AbstractRepository):
        self.repo = repo
        self.exception = NotAuthorized()

    @property
    def config(self) -> AuthorizationConfiguration:
        return self.repo.get_config()

    def require(self, role: Role | None = None, roles: set[Role] | None = None, scopes=list[str]):
        if role is None and roles is None:
            raise DomainException("AuthorizationService.require needs at least one Role.")
        if role and roles:
            raise DomainException(
                "AuthorizationService.require cannot handle both role and roles."
            )

        required_roles = {role} if role else roles
        if any(self.is_allowed(scopes, role) for role in required_roles):
            return GRANTED
        raise self.exception

    def permit(
        self,
        *args,
        team_id: int,
        scopes: list[str],
        data: dict,
        permission: Permission,
    ):
        if not permission:
            raise DomainException("AuthorizationService.permit needs a Permission")
        fields = set(data.keys())
        for role in self.get_applicable_roles(team_id, scopes):
            if permission.role == role and permission.can_access_fields(fields):
                return GRANTED

        return DENIED

    def get_applicable_roles(self, team_id, scopes):
        team_scope = self.config.team_id_to_scope(team_id)
        roles = {self.config.scope_to_role(scope) for scope in scopes}
        if team_scope not in scopes:
            roles.discard(Role.TEAM_MEMBER)
        return roles

    def is_team_member(
        self,
        *args,
        **kwargs,
    ):
        data = kwargs.get("data", {})
        scopes = kwargs.get("scopes", {})
        team_id = data.get("team_id")
        product_id = kwargs.get("product_id")
        if not team_id and not product_id:
            raise DomainException(
                "AuthorizationService.is_team_member needs either a team_id or product_id"
            )
        if team_id:
            team_scope = self.config.team_id_to_scope(team_id)
        else:
            team_scope = self.config.product_id_to_scope(product_id)

        if team_scope in scopes:
            return GRANTED
        return DENIED

    def is_allowed(self, scopes: list[str], role: Role):
        return any(self.config.scope_to_role(scope) == role for scope in scopes)


class Authorizer:
    AND = "AND"
    OR = "OR"

    def __init__(self):
        self._register = {}

    def __call__(auth_self, *auth_types, mode=OR):
        def decorator(func):
            def wrapper(self, *args, **kwargs):
                try:
                    authorization_functions = [
                        auth_self._register[auth_type] for auth_type in auth_types
                    ]
                except KeyError:
                    raise DomainException(
                        f"One or more of these auth_types do not exist: {auth_types}"
                    ) from None
                if mode == auth_self.OR:
                    # any of the functions should pass
                    allowed = any(
                        f(self, *args, **kwargs) == GRANTED for f in authorization_functions
                    )
                else:
                    # all of the functions should pass
                    allowed = all(
                        f(self, *args, **kwargs) == GRANTED for f in authorization_functions
                    )
                if not allowed:
                    raise NotAuthorized("You are not authorized to perform this operation")
                return func(self, *args, **kwargs)

            return wrapper

        return decorator

    def register_auth(
        self, auth_type: str, method: callable, permission: Permission | None = None
    ):
        self._register[auth_type] = lambda self, *args, **kwargs: method(
            *args, permission=permission, **kwargs
        )


authorize = Authorizer()
