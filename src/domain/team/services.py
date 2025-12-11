from domain.auth import authorize
from domain.base import AbstractRepository, AbstractService
from domain.team import Team


class TeamService(AbstractService):
    repository: AbstractRepository[Team]

    def __init__(self, repo: AbstractRepository[Team], **kwargs):
        self.repository = repo

    def refresh(self):
        self.repository.refresh_from_db()

    def get_team(self, team_id: str) -> Team:
        return self.repository.get(team_id)

    def get_teams(self) -> list[Team]:
        return self.repository.list()

    def get_team_by_name(self, name: str) -> Team:
        return self.repository.get_by_name(name)

    def get_teams_from_scopes(self, scopes) -> list[Team]:
        all_teams = self.get_teams()
        return [team for team in all_teams if team.scope in scopes]

    @authorize.is_admin
    def create_team(self, *, data, **kwargs) -> Team:
        team = Team(**data)
        return self._persist(team)

    @authorize.is_admin
    @authorize.can_update_team
    def update_team(self, *, team_id: int, data: dict, **kwargs) -> Team:
        team = self.get_team(team_id)
        team.update_from_dict(data)
        return self._persist(team)

    @authorize.is_admin
    def delete_team(self, team_id: int, **kwargs) -> None:
        return self.repository.delete(team_id)

    def _persist(self, team: Team) -> None:
        return self.repository.save(team)
