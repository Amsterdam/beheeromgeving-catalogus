from domain import exceptions
from domain.auth.objects import AuthorizationConfiguration, Role


class AuthorizationService:
    config: AuthorizationConfiguration

    def configure(self, admin_role: str, team_scopes: list[str]):
        self.config = AuthorizationConfiguration(admin_role, team_scopes)

    def require(self, role: Role):
        def wrapper(func):
            def wrapped(*args, **kwargs):
                scopes = kwargs.get("scopes", [])
                if self.is_allowed(scopes, role):
                    return func(*args, **kwargs)
                else:
                    raise exceptions.NotAuthorized(
                        "You are not authorized to perform this operation"
                    )

            return wrapped

        return wrapper

    def is_allowed(self, scopes: list[str], role: Role):
        if not hasattr(self, "config"):
            raise exceptions.DomainException("AuthorizationSerice is not configured!")
        return any(self.config.scope_to_role(scope) == role for scope in scopes)
