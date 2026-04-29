from django.conf import settings
from django.db.models import QuerySet

from beheeromgeving import models as orm
from domain.auth import AuthorizationConfiguration
from domain.base import AbstractAuthRepository


class AuthorizationRepository(AbstractAuthRepository):
    def __init__(self):
        self.queryset: QuerySet[orm.Team] = orm.Team.objects.all()
        self.admin_role: str = settings.ADMIN_ROLE_NAME
        self.employee_role: str = settings.EMPLOYEE_ROLE_NAME
        self.feature_enabled: bool = settings.FEATURE_FLAG_USE_AUTH

    def get_config(self) -> AuthorizationConfiguration:
        product_scopes = {}
        team_scopes = {}

        for t in self.queryset:
            team_scopes[t.pk] = t.scope
            for p in t.products.all():
                product_scopes[p.pk] = t.scope
                if p.name:
                    product_scopes[p.name.lower()] = t.scope
        return AuthorizationConfiguration(
            self.admin_role,
            self.employee_role,
            team_scopes,
            product_scopes,
            feature_enabled=self.feature_enabled,
        )
