from domain import exceptions
from domain.auth import AuthorizationConfiguration, Permissions, Role
from domain.base import AbstractRepository


class AuthorizationService:

    def __init__(self, repo: AbstractRepository):
        self.repo = repo

    @property
    def config(self) -> AuthorizationConfiguration:
        return self.repo.get_config()

    def require(self, role: Role | None = None, roles: set[Role] | None = None, scopes=list[str]):
        if role is None and roles is None:
            raise exceptions.DomainException(
                "AuthorizationService.require needs at least one Role."
            )
        if role and roles:
            raise exceptions.DomainException(
                "AuthorizationService.require cannot handle both role and roles."
            )

        required_roles = {role} if role else roles
        if not any(self.is_allowed(scopes, role) for role in required_roles):
            raise exceptions.NotAuthorized("You are not authorized to perform this operation")

    def permit(self, permissions: Permissions | None = None, scopes=list[str], fields=list[str]):
        if permissions is None:
            raise exceptions.DomainException("AuthorizationService.permit needs Permissions")
        roles = {self.config.scope_to_role(scope) for scope in scopes}
        if not permissions.can_access_fields(roles, fields):
            raise exceptions.NotAuthorized("You are not authorized to perform this operation")

    def is_allowed(self, scopes: list[str], role: Role):
        return any(self.config.scope_to_role(scope) == role for scope in scopes)
