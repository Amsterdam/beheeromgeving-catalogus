from django.conf import settings

from beheeromgeving import models as orm
from domain.auth import AuthorizationConfiguration
from domain.base import AbstractAuthRepository


class AuthorizationRepository(AbstractAuthRepository):
    def __init__(self):
        self.queryset = orm.Team.objects.all()
        self.admin_role: str = settings.ADMIN_ROLE_NAME
        self.feature_enabled: bool = settings.FEATURE_FLAG_USE_AUTH

    def get_config(self) -> AuthorizationConfiguration:
        team_scopes = {t.id: t.scope for t in self.queryset}
        product_scopes = {p.id: t.scope for t in self.queryset for p in t.products.all()}
        return AuthorizationConfiguration(
            self.admin_role, team_scopes, product_scopes, feature_enabled=self.feature_enabled
        )
