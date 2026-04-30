from domain import exceptions
from domain.auth import Scope, authorize
from domain.product import enums
from domain.product.policies import ProductReadLevel, ProductReadPolicy
from domain.product.repositories import ProductRepository
from domain.team import Team


class ProductQueryHandler:
    def __init__(self, repository: ProductRepository):
        self.repository = repository

    def list_products(self, *, scopes: list[Scope] | None = None, **kwargs):
        if authorize.auth is None:
            raise exceptions.DomainException(
                "Authorizer doesn't have an AuthorizationService, please call set_auth_service()"
            )
        policy = ProductReadPolicy(authorize.auth)
        level = policy.level(scopes=scopes)
        if level in (ProductReadLevel.FULL, ProductReadLevel.INTERNAL):
            return self.repository.list_for_publication_status(
                [
                    enums.PublicationStatus.INTERNALLY_PUBLISHED,
                    enums.PublicationStatus.PUBLISHED,
                ],
                **kwargs,
            )
        return self.repository.list_for_publication_status(
            [enums.PublicationStatus.PUBLISHED],
            **kwargs,
        )

    def list_my_products(self, teams: list[Team], **kwargs):
        return self.repository.list_mine(teams=teams, **kwargs)
