from functools import wraps

from domain.auth import (
    RULES,
    AuthorizationConfiguration,
    AuthorizationResult,
    Permission,
    Role,
    Rule,
)
from domain.base import AbstractAuthRepository
from domain.exceptions import DomainException, NotAuthorized


class AuthorizationService:

    def __init__(self, repo: AbstractAuthRepository):
        self.repo = repo

    def refresh(self):
        self.repo.refresh_from_db()

    @property
    def config(self) -> AuthorizationConfiguration:
        return self.repo.get_config()

    def require(
        self,
        *args,
        scopes: list[str],
        role: Role | None = None,
        **kwargs,
    ) -> AuthorizationResult:
        """Assert that the user has the required role."""
        if role is None:
            raise DomainException("AuthorizationService.require needs a Role.")

        if self.is_allowed(scopes, role):
            return AuthorizationResult.GRANTED
        return AuthorizationResult.DENIED

    def permit(
        self,
        *args,
        team_id: int,
        scopes: list[str],
        data: dict,
        permission: Permission,
        **kwargs,
    ) -> AuthorizationResult:
        """Assert that the user can perform the action on all the fields in the data."""
        if not permission:
            raise DomainException("AuthorizationService.permit needs a Permission")
        fields = set(data.keys())
        for role in self.get_applicable_roles(team_id, scopes):
            if permission.role == role and permission.can_access_fields(fields):
                return AuthorizationResult.GRANTED

        return AuthorizationResult.DENIED

    def get_applicable_roles(self, team_id: int, scopes: list[str]):
        team_scope = self.config.team_id_to_scope(team_id)
        roles = {self.config.scope_to_role(scope) for scope in scopes}
        if team_scope not in scopes:
            roles.discard(Role.TEAM_MEMBER)
        return roles

    def is_team_member(
        self,
        *args,
        scopes: list[str],
        data: dict | None = None,
        product_id: int | None = None,
        **kwargs,
    ) -> AuthorizationResult:
        """Assert the user is a member of the team that owns the resource."""
        if data is None:
            data = {}
        team_id: int = data.get("team_id")
        if not team_id and not product_id:
            raise DomainException(
                "AuthorizationService.is_team_member needs either a team_id or product_id"
            )
        if team_id:
            team_scope = self.config.team_id_to_scope(team_id)
        else:
            team_scope = self.config.product_id_to_scope(product_id)

        if team_scope in scopes:
            return AuthorizationResult.GRANTED
        return AuthorizationResult.DENIED

    def is_allowed(self, scopes: list[str], role: Role):
        return any(self.config.scope_to_role(scope) == role for scope in scopes)


class Authorizer:
    """Syntactic sugar around the AuthorizationService that allows us to use
    decorators to do all the authorization checks.

    Initialization:
    ```
    authorize = Authorizer()
    authorize.set_auth_service(AuthorizationService(repo=AuthorizationRepository))
    ```
    Usage:

    ```
    class SomeService:
        ...

        @authorize.is_admin
        def protected_method(self, *args, **kwargs):
            pass
    ```

    The decorators are created dynamically, based on the RULES defined in auth/objects.py
    """

    def __init__(self):
        self.auth = None
        for rule in RULES:
            self.register_auth(rule)

    def set_auth_service(self, auth: AuthorizationService):
        self.auth = auth
        self.NO_AUTH = not auth.config.feature_enabled

    def _create_lambda(self, rule: Rule):
        if self.auth is None:
            raise DomainException(
                "Authorizer doesn't have an AuthorizationService, please call set_auth_service()"
            )
        try:
            service_method = getattr(self.auth, rule.method_name)
            return lambda self, *args, **kwargs: service_method(
                *args, permission=rule.permission, role=rule.role, **kwargs
            )
        except AttributeError:
            raise DomainException(
                f"Method {rule.method_name} does not exist on AuthorizationService"
            ) from None

    def _create_decorator(auth_self, rule: Rule):
        def decorator(func):
            @wraps(func)
            def wrapper(self, *args, **kwargs):
                if auth_self.NO_AUTH:
                    return func(self, *args, **kwargs)
                already_allowed = kwargs.pop("already_allowed", False)
                if already_allowed:
                    return func(self, *args, **kwargs)
                try:
                    authorization_function = auth_self._create_lambda(rule)
                except KeyError:
                    raise DomainException(
                        f"Authorization Type does not exist: {rule.decorator_name}"
                    ) from None
                allowed = (
                    authorization_function(self, *args, **kwargs) == AuthorizationResult.GRANTED
                )
                if hasattr(func, "__wrapped__"):
                    return func(self, *args, already_allowed=allowed, **kwargs)

                if not allowed:
                    raise NotAuthorized("You are not authorized to perform this operation.")
                return func(self, *args, **kwargs)

            return wrapper

        return decorator

    def register_auth(self, rule: Rule):
        decorator = self._create_decorator(rule)
        setattr(self, rule.decorator_name, decorator)


authorize = Authorizer()
