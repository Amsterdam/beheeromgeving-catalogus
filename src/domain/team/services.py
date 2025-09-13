from domain import exceptions
from domain.auth import authorize
from domain.base import (
    AbstractService,
    AbstractTeamRepository,
)
from domain.team import Team


class TeamService:
    repository: AbstractTeamRepository
    auth: AbstractService

    def __init__(self, repo: AbstractTeamRepository, auth: AbstractService, **kwargs):
        self.repository = repo
        self.auth = auth

    def get_team(self, team_id: str) -> Team:
        return self.repository.get(team_id)

    def get_teams(self) -> list[Team]:
        return self.repository.list()

    @authorize.is_admin
    def create_team(self, *, data, scopes) -> Team:
        if data.get("id"):
            raise exceptions.IllegalOperation("IDs are assigned automatically")
        team = Team(**data)
        return self._persist(team)

    @authorize.is_admin
    @authorize.can_update_team
    def update_team(self, team_id: int, **kwargs) -> Team:
        data = kwargs.get("data", {})
        if int(data.get("id", team_id)) != int(team_id):
            raise exceptions.IllegalOperation("Cannot update product id")
        team = self.get_team(team_id)
        team.update_from_dict(data)
        return self._persist(team)

    @authorize.is_admin
    def delete_team(self, team_id, *, scopes) -> None:
        return self.repository.delete(team_id)

    def _persist(self, team: Team) -> None:
        return self.repository.save(team)
