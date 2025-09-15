from functools import wraps

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

    def require(
        self,
        *args,
        role: Role | None = None,
        scopes=list[str],
        **kwargs,
    ):
        if role is None:
            raise DomainException("AuthorizationService.require needs a Role.")

        if self.is_allowed(scopes, role):
            return GRANTED
        return DENIED

    def permit(
        self,
        *args,
        team_id: int,
        scopes: list[str],
        data: dict,
        permission: Permission,
        **kwargs,
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
    def __init__(self):
        self.auth = None
        TEAM_UPDATE_PERMISSION = Permission(
            role=Role.TEAM_MEMBER, allowed_fields={"po_name", "po_email", "contact_email"}
        )
        self.register_auth("is_team_member")
        self.register_auth("can_update_team", "permit", permission=TEAM_UPDATE_PERMISSION)
        self.register_auth("is_admin", "require", role=Role.ADMIN)

    def set_auth_service(self, auth):
        self.auth = auth

    def _create_lambda(self, method_name, permission, role):
        if self.auth is None:
            raise DomainException(
                "Authorizer doesn't have an AuthorizationService, please call set_auth_service()"
            )
        try:
            service_method = getattr(self.auth, method_name)
            return lambda self, *args, **kwargs: service_method(
                *args, permission=permission, role=role, **kwargs
            )
        except AttributeError:
            raise DomainException(
                f"Method {method_name} does not exist on AuthorizationService"
            ) from None

    def _create_decorator(auth_self, auth_type, service_method_name, permission, role):
        def decorator(func):
            @wraps(func)
            def wrapper(self, *args, **kwargs):
                already_allowed = kwargs.pop("already_allowed", False)
                if already_allowed:
                    return func(self, *args, **kwargs)
                try:
                    authorization_function = auth_self._create_lambda(
                        service_method_name, permission, role
                    )
                except KeyError:
                    raise DomainException(
                        f"Authorization Type does not exist: {auth_type}"
                    ) from None
                allowed = authorization_function(self, *args, **kwargs) == GRANTED
                if hasattr(func, "__wrapped__"):
                    return func(self, *args, already_allowed=allowed, **kwargs)

                if not allowed:
                    raise NotAuthorized(
                        f"You are not authorized to perform this operation {auth_type}"
                    )
                return func(self, *args, **kwargs)

            return wrapper

        return decorator

    def register_auth(
        self,
        auth_type: str,
        service_method_name: str | None = None,
        permission: Permission | None = None,
        role: Role | None = None,
    ):
        if service_method_name is None:
            service_method_name = auth_type
        decorator = self._create_decorator(auth_type, service_method_name, permission, role)
        setattr(self, auth_type, decorator)


authorize = Authorizer()
