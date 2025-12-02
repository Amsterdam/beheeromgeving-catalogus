from django.db.utils import IntegrityError

from beheeromgeving import models as orm
from domain import exceptions
from domain.base import AbstractRepository
from domain.team import Team


class TeamRepository(AbstractRepository):
    _teams: dict[int, Team]

    def __init__(self):
        self.refresh_from_db()

    def refresh_from_db(self) -> None:
        self._teams = {t.id: t.to_domain() for t in orm.Team.objects.all()}

    def get(self, team_id: int) -> Team:
        try:
            return self._teams[team_id]
        except KeyError as e:
            raise exceptions.ObjectDoesNotExist(f"Team with id {team_id} does not exist") from e

    def get_by_name(self, name: str) -> Team:
        try:
            normalized_name = name.replace("_", " ").lower()
            return next(
                team
                for team in self._teams.values()
                if normalized_name.startswith(team.name.lower())
            )
        except StopIteration as e:
            raise exceptions.ObjectDoesNotExist(f"Team with name {name} does not exist") from e

    def list(self) -> list[Team]:
        return list(self._teams.values())

    def save(self, team: Team) -> int:
        try:
            saved_team = orm.Team.from_domain(team)
        except IntegrityError:
            raise exceptions.ValidationError(f"Team {team.acronym} already exists") from None
        self._teams[saved_team.id] = saved_team
        return saved_team.id

    def delete(self, team_id: int) -> int:
        try:
            self._teams.pop(team_id)
        except KeyError as e:
            raise exceptions.ObjectDoesNotExist(f"Team with id {team_id} does not exist") from e

        orm.Team.objects.filter(id=team_id).delete()
        return team_id
