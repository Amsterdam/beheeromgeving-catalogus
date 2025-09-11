from django.conf import settings

from beheeromgeving import models as orm
from domain.auth import AuthorizationConfiguration
from domain.base import AbstractAuthRepository


class AuthorizationRepository(AbstractAuthRepository):
    def __init__(self):
        team_scopes = [t.scope for t in orm.Team.objects.all()]
        admin_role = settings.ADMIN_ROLE_NAME
        self.config = AuthorizationConfiguration(admin_role, team_scopes)

    def get_config(self) -> AuthorizationConfiguration:
        return self.config
