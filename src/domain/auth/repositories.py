from django.conf import settings

from beheeromgeving import models as orm
from domain.auth import AuthorizationConfiguration
from domain.base import AbstractAuthRepository


class AuthorizationRepository(AbstractAuthRepository):
    def __init__(self):
        queryset = orm.Team.objects.all()
        team_scopes = {t.id: t.scope for t in queryset}
        product_scopes = {p.id: t.scope for t in queryset for p in t.products.all()}
        admin_role: str = settings.ADMIN_ROLE_NAME
        feature_enabled: bool = settings.FEATURE_FLAG_USE_AUTH
        self.config = AuthorizationConfiguration(
            admin_role, team_scopes, product_scopes, feature_enabled=feature_enabled
        )

    def get_config(self) -> AuthorizationConfiguration:
        return self.config
