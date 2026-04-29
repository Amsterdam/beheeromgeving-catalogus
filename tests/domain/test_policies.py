from django.conf import settings

from domain.product.policies import ProductReadLevel, ProductReadPolicy


class TestProductReadPolicy:
    def test_level_for_product_admin(self, auth_service, product):
        assert product.id
        policy = ProductReadPolicy(auth=auth_service)

        assert (
            policy.level_for_product(product_id=product.id, scopes=[settings.ADMIN_ROLE_NAME])
            is ProductReadLevel.FULL
        )

    def test_level_for_product_team_member(self, auth_service, product, team):
        assert product.id
        policy = ProductReadPolicy(auth=auth_service)

        assert (
            policy.level_for_product(product_id=product.id, scopes=[team.scope])
            is ProductReadLevel.FULL
        )

    def test_level_for_product_employee(self, auth_service, product):
        assert product.id
        policy = ProductReadPolicy(auth=auth_service)

        assert (
            policy.level_for_product(
                product_id=product.id,
                scopes=[settings.EMPLOYEE_ROLE_NAME],
            )
            is ProductReadLevel.INTERNAL
        )

    def test_level_for_product_anonymous(self, auth_service, product):
        assert product.id
        policy = ProductReadPolicy(auth=auth_service)

        assert (
            policy.level_for_product(product_id=product.id, scopes=[])
            is ProductReadLevel.PUBLISHED
        )

    def test_level_for_product_scopes_none(self, auth_service, product):
        assert product.id
        policy = ProductReadPolicy(auth=auth_service)

        assert (
            policy.level_for_product(product_id=product.id, scopes=None)
            is ProductReadLevel.PUBLISHED
        )

    def test_level_for_product_name_team_member(self, auth_service, product, team):
        assert product.name
        policy = ProductReadPolicy(auth=auth_service)

        assert (
            policy.level_for_product_name(name=product.name, scopes=[team.scope])
            is ProductReadLevel.FULL
        )

    def test_level_for_product_name_employee_is_published(self, auth_service, product):
        assert product.name
        policy = ProductReadPolicy(auth=auth_service)

        assert (
            policy.level_for_product_name(name=product.name, scopes=[settings.EMPLOYEE_ROLE_NAME])
            is ProductReadLevel.PUBLISHED
        )

    def test_level(self, auth_service, product):
        assert product.id
        policy = ProductReadPolicy(auth=auth_service)

        assert policy.level(scopes=[settings.ADMIN_ROLE_NAME]) is ProductReadLevel.FULL
        assert policy.level(scopes=[settings.EMPLOYEE_ROLE_NAME]) is ProductReadLevel.INTERNAL
        assert policy.level(scopes=[]) is ProductReadLevel.PUBLISHED
        assert policy.level(scopes=None) is ProductReadLevel.PUBLISHED
