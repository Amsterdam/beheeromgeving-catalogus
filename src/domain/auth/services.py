from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, Protocol, TypeVar

from domain.auth import (
    RULES,
    AuthorizationResult,
    Permission,
    ProductId,
    Role,
    Rule,
    Scope,
    TeamId,
)
from domain.base import AbstractAuthRepository
from domain.exceptions import DomainException, NotAuthenticated, NotAuthorized


class AuthorizationService:
    def __init__(self, repo: AbstractAuthRepository):
        self.repo = repo

    @property
    def feature_enabled(self) -> bool:
        return self.repo.feature_enabled

    @property
    def admin_role(self) -> str:
        return self.repo.admin_role

    @property
    def employee_role(self) -> str:
        return self.repo.employee_role

    def require(
        self,
        *args,
        scopes: list[Scope],
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
        team_id: TeamId,
        scopes: list[Scope],
        data: dict,
        permission: Permission,
        **kwargs,
    ) -> AuthorizationResult:
        """Assert that the user can perform the action on all the fields in the data.

        For now only used for the team member role."""
        if not permission:
            raise DomainException("AuthorizationService.permit needs a Permission")
        fields = set(data.keys())
        if (
            self.repo.can_access_team(int(team_id), scopes)
            and permission.role == Role.TEAM_MEMBER
            and permission.can_access_fields(fields)
        ):
            return AuthorizationResult.GRANTED

        return AuthorizationResult.DENIED

    def is_team_member(
        self,
        *args,
        scopes: list[Scope],
        data: dict | None = None,
        product_id: ProductId | None = None,
        name: str | None = None,
        **kwargs,
    ) -> AuthorizationResult:
        """Assert the user is a member of the team that owns the resource."""
        if data is None:
            data = {}
        team_id = data.get("team_id")
        if not team_id and not product_id and not name:
            raise DomainException(
                "AuthorizationService.is_team_member needs either a team_id, product_id, "
                "or (product) name."
            )

        if (
            (team_id and self.repo.can_access_team(int(team_id), scopes))
            or (product_id and self.repo.can_access_product(int(product_id), scopes))
            or (name and self.repo.can_access_product_name(str(name), scopes))
        ):
            return AuthorizationResult.GRANTED
        else:
            return AuthorizationResult.DENIED

    def is_allowed(self, scopes: list[Scope], role: Role):
        if role is Role.ADMIN:
            return self.admin_role in scopes
        if role is Role.EMPLOYEE:
            return self.employee_role in scopes
        return False

    def has_role(self, *, scopes: list[Scope], role: Role) -> bool:
        return self.require(scopes=scopes, role=role) == AuthorizationResult.GRANTED

    def is_admin(self, *, scopes: list[Scope]) -> bool:
        return self.has_role(scopes=scopes, role=Role.ADMIN)

    def is_employee(self, *, scopes: list[Scope]) -> bool:
        return self.has_role(scopes=scopes, role=Role.EMPLOYEE)

    def is_team_member_of_product(self, *, product_id: ProductId, scopes: list[Scope]) -> bool:
        return (
            self.is_team_member(scopes=scopes, product_id=product_id)
            == AuthorizationResult.GRANTED
        )

    def is_team_member_of_team(self, *, team_id: TeamId, scopes: list[Scope]) -> bool:
        return (
            self.is_team_member(scopes=scopes, data={"team_id": team_id})
            == AuthorizationResult.GRANTED
        )

    def is_team_member_of_product_name(self, *, name: str, scopes: list[Scope]) -> bool:
        return self.is_team_member(scopes=scopes, name=name) == AuthorizationResult.GRANTED


P = ParamSpec("P")
R = TypeVar("R")


class AuthorizationDecorator(Protocol):
    def __call__(self, func: Callable[P, R]) -> Callable[P, R]: ...


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
        self.decorators = {}
        for rule in RULES:
            self.register_auth(rule)

    def __getattr__(self, name: str) -> AuthorizationDecorator:
        return self.decorators[name]

    def set_auth_service(self, auth: AuthorizationService):
        self.auth = auth
        self.NO_AUTH = not auth.feature_enabled

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

                scopes = kwargs.get("scopes")
                if not scopes:
                    raise NotAuthenticated("Authentication required.")

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
        self.decorators[rule.decorator_name] = decorator


authorize = Authorizer()
