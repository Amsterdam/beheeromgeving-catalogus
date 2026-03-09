from domain.product.repositories import ProductRepository
from domain.team import Team


class ProductQueryHandler:
    def __init__(self, repository: ProductRepository):
        self.repository = repository

    def list_products(self, **kwargs):
        return self.repository.list(**kwargs)

    def list_my_products(self, teams: list[Team], **kwargs):
        return self.repository.list_mine(teams=teams, **kwargs)
