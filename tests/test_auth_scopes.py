import pytest

from domain.auth import AuthorizationResult, ProductId, Scope
from domain.auth.repositories import AuthorizationRepository
from domain.auth.services import AuthorizationService
from domain.base import AbstractAuthRepository


@pytest.mark.django_db
def test_auth_repository_scope_lookups(orm_team, orm_product):
    repo = AuthorizationRepository()
    assert repo.can_access_team(orm_team.pk, scopes=[Scope(orm_team.scope)]) is True
    assert repo.can_access_product(orm_product.pk, scopes=[Scope(orm_team.scope)]) is True
    assert repo.can_access_product_name(orm_product.name, scopes=[Scope(orm_team.scope)]) is True


@pytest.mark.django_db
def test_auth_repository_scope_lookups_missing_return_denied():
    repo = AuthorizationRepository()

    assert repo.can_access_team(999999, scopes=[Scope("scope_team")]) is False
    assert repo.can_access_product(999999, scopes=[Scope("scope_team")]) is False
    assert repo.can_access_product_name("does-not-exist", scopes=[Scope("scope_team")]) is False


def test_authorization_service_does_not_need_get_config():
    class Repo(AbstractAuthRepository):
        feature_enabled = True
        admin_role = "admin"
        employee_role = "employee"

        def can_access_team(self, team_id: int, scopes):
            return Scope("scope_team") in scopes

        def can_access_product(self, product_id: int, scopes):
            return Scope("scope_team") in scopes

        def can_access_product_name(self, name: str, scopes):
            return Scope("scope_team") in scopes

    service = AuthorizationService(repo=Repo())

    assert service.is_admin(scopes=[Scope("admin")]) is True
    assert service.is_employee(scopes=[Scope("employee")]) is True

    # team membership check uses repo lookups
    assert (
        service.is_team_member(scopes=[Scope("scope_team")], product_id=ProductId(1))
        == AuthorizationResult.GRANTED
    )
