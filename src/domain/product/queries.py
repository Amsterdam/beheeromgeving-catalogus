from domain.auth import authorize
from domain.product.repositories import ProductRepository
from domain.team import Team


class ProductQueryHandler:
    def __init__(self, repository: ProductRepository):
        self.repository = repository

    @authorize.is_admin
    @authorize.is_employee
    def list_internal_products(self, scopes, **kwargs):
        return self.repository.list_internal(**kwargs)

    def list_products(self, **kwargs):
        return self.repository.list(**kwargs)

    def list_my_products(self, teams: list[Team], **kwargs):
        return self.repository.list_mine(teams=teams, **kwargs)
