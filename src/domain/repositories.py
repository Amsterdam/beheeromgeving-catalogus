import abc

from beheeromgeving import models as orm
from domain import exceptions, objects


class AbstractRepository(abc.ABC):
    @abc.abstractmethod
    def get(self, ref):
        raise NotImplementedError

    @abc.abstractmethod
    def list(self):
        raise NotImplementedError

    @abc.abstractmethod
    def save(self, ref, data):
        raise NotImplementedError

    @abc.abstractmethod
    def delete(self, ref):
        raise NotImplementedError


class TeamRepository(AbstractRepository):
    _teams = dict[int, objects.Team]

    def __init__(self):
        self._teams = {t.id: t.to_domain() for t in orm.Team.objects.all()}

    def get(self, team_id: int) -> objects.Team:
        try:
            return self._teams[team_id]
        except KeyError as e:
            raise exceptions.ObjectDoesNotExist(f"Team with id {team_id} does not exist") from e

    def list(self):
        return list(self._teams.values())

    def save(self, team: objects.Team):
        saved_team = orm.Team.from_domain(team)
        self._teams[saved_team.id] = saved_team
        return saved_team.id

    def delete(self, team_id: int):
        try:
            self._teams.pop(team_id)
        except KeyError as e:
            raise exceptions.ObjectDoesNotExist(f"Team with id {team_id} does not exist") from e

        orm.Team.objects.filter(id=team_id).delete()
        return team_id


class ProductRepository(AbstractRepository):
    _products: dict[int, objects.Product]

    def __init__(self):
        self._products = {p.id: p.to_domain() for p in orm.Product.objects.all()}

    def get(self, product_id: int) -> objects.Product:
        try:
            return self._products[product_id]
        except KeyError as e:
            raise exceptions.ObjectDoesNotExist from e

    def list(self, **kwargs):
        return list(self._products.values())

    def save(self, product: objects.Product):
        saved_product = orm.Product.from_domain(product)
        self._products[saved_product.id] = saved_product
        return saved_product.id

    def delete(self, product_id: int):
        try:
            self._products.pop(product_id)
        except KeyError as e:
            raise exceptions.ObjectDoesNotExist from e

        orm.Product.objects.filter(id=product_id).delete()
        return product_id
