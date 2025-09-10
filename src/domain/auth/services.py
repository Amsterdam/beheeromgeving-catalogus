from domain import exceptions
from domain.auth.objects import AuthorizationConfiguration, Permissions, Role


class AuthorizationService:
    _config: AuthorizationConfiguration

    def configure(self, admin_role: str, team_scopes: list[str]):
        self._config = AuthorizationConfiguration(admin_role, team_scopes)

    @property
    def config(self):
        if not hasattr(self, "_config"):
            raise exceptions.DomainException("AuthorizationSerice is not configured!")
        return self._config

    def require(self, role: Role | None = None, permissions: Permissions | None = None):
        if not role and not permissions:
            raise exceptions.DomainException(
                "AuthorizationService.require needs either a Role or Permissions"
            )

        def wrapper(func):
            def wrapped(*args, **kwargs):
                if role is not None:
                    scopes = kwargs.get("scopes", [])
                    if self.is_allowed(scopes, role):
                        return func(*args, **kwargs)
                    else:
                        raise exceptions.NotAuthorized(
                            "You are not authorized to perform this operation"
                        )
                else:
                    scopes = kwargs.get("scopes", [])
                    roles = {self.config.scope_to_role(scope) for scope in scopes}
                    fields = set(kwargs.get("data", {}).keys())
                    print(permissions)
                    if permissions.can_access_fields(roles, fields):
                        return func(*args, **kwargs)
                    else:
                        raise exceptions.NotAuthorized(
                            "You are not authorized to perform this operation"
                        )

            return wrapped

        return wrapper

    def is_allowed(self, scopes: list[str], role: Role):
        return any(self.config.scope_to_role(scope) == role for scope in scopes)
