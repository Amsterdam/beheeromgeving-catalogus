from beheeromgeving import models as orm
from domain import exceptions
from domain.base import AbstractRepository
from domain.team import Team


class TeamRepository(AbstractRepository):
    _teams = dict[int, Team]

    def __init__(self):
        self._teams = {t.id: t.to_domain() for t in orm.Team.objects.all()}

    def get(self, team_id: int) -> Team:
        try:
            return self._teams[team_id]
        except KeyError as e:
            raise exceptions.ObjectDoesNotExist(f"Team with id {team_id} does not exist") from e

    def list(self) -> list[Team]:
        return list(self._teams.values())

    def save(self, team: Team) -> int:
        saved_team = orm.Team.from_domain(team)
        self._teams[saved_team.id] = saved_team
        return saved_team.id

    def delete(self, team_id: int) -> int:
        try:
            self._teams.pop(team_id)
        except KeyError as e:
            raise exceptions.ObjectDoesNotExist(f"Team with id {team_id} does not exist") from e

        orm.Team.objects.filter(id=team_id).delete()
        return team_id
