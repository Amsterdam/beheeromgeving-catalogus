from django.conf import settings

from beheeromgeving import models as orm
from domain.auth import Scope
from domain.base import AbstractAuthRepository


class AuthorizationRepository(AbstractAuthRepository):
    def __init__(self):
        self.admin_role: str = settings.ADMIN_ROLE_NAME
        self.employee_role: str = settings.EMPLOYEE_ROLE_NAME
        self.feature_enabled: bool = settings.FEATURE_FLAG_USE_AUTH

    def can_access_team(self, team_id: int, scopes: list[Scope]) -> bool:
        return orm.Team.objects.filter(pk=team_id, scope__in=scopes).exists()

    def can_access_product(self, product_id: int, scopes: list[Scope]) -> bool:
        return orm.Product.objects.filter(pk=product_id, team__scope__in=scopes).exists()

    def can_access_product_name(self, name: str, scopes: list[Scope]) -> bool:
        return orm.Product.objects.filter(name__iexact=name, team__scope__in=scopes).exists()
