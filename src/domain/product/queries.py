from domain.auth import Scope, authorize
from domain.product.policies import ProductReadLevel, ProductReadPolicy
from domain.product.repositories import ProductRepository
from domain.team import Team


class ProductQueryHandler:
    def __init__(self, repository: ProductRepository):
        self.repository = repository

    def list_products(self, *, scopes: list[Scope] | None = None, **kwargs):
        policy = ProductReadPolicy(authorize.auth)
        data = []
        level = policy.level(scopes=scopes)
        if level in (ProductReadLevel.FULL, ProductReadLevel.INTERNAL):
            data.extend(self.repository.list_internal(**kwargs))
        data.extend(self.repository.list(**kwargs))
        return data

    def list_my_products(self, teams: list[Team], **kwargs):
        return self.repository.list_mine(teams=teams, **kwargs)
