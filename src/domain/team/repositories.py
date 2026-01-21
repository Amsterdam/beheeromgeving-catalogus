from django.db.models import F, QuerySet, Value
from django.db.utils import IntegrityError

from beheeromgeving import models as orm
from domain import exceptions
from domain.base import AbstractRepository
from domain.team import Team

# alias for typing
list_ = list


class TeamRepository(AbstractRepository[Team]):
    qs: QuerySet[orm.Team]

    def __init__(self):
        self.qs = orm.Team.objects.all()

    def get(self, id: int) -> Team:
        try:
            return self.qs.get(pk=id).to_domain()
        except orm.Team.DoesNotExist as e:
            raise exceptions.ObjectDoesNotExist(f"Team with id {id} does not exist") from e

    def get_by_name(self, name: str) -> Team:
        team = (
            self.qs.annotate(search_name=Value(name))
            .filter(search_name__istartswith=F("name"))
            .first()
        )
        if not team:
            raise exceptions.ObjectDoesNotExist(f"Team with name {name} does not exist")
        return team.to_domain()

    def list(self) -> list_[Team]:
        return [t.to_domain() for t in self.qs]

    def save(self, item: Team) -> Team:
        try:
            saved_team = orm.Team.from_domain(item)
        except IntegrityError:
            raise exceptions.ValidationError(f"Team {item.acronym} already exists") from None
        return saved_team

    def delete(self, id: int) -> int:
        num_deleted, _ = orm.Team.objects.filter(id=id).delete()
        if num_deleted == 0:
            raise exceptions.ObjectDoesNotExist(f"Team with id {id} does not exist")
        return id
