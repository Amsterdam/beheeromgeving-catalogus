from domain import exceptions
from domain.auth import Permissions, Role
from domain.base import (
    AbstractService,
    AbstractTeamRepository,
)
from domain.team import Team


class TeamService:
    repository: AbstractTeamRepository
    auth: AbstractService

    def __init__(self, repo: AbstractTeamRepository, auth: AbstractService):
        self.repository = repo
        self.auth = auth

    def get_team(self, team_id: str) -> Team:
        return self.repository.get(team_id)

    def get_teams(self) -> list[Team]:
        return self.repository.list()

    def create_team(self, *, data, scopes) -> Team:
        self.auth.require(role=Role.ADMIN, scopes=scopes)
        if data.get("id"):
            raise exceptions.IllegalOperation("IDs are assigned automatically")
        team = Team(**data)
        return self._persist(team)

    UPDATE_TEAM_PERMISSION = Permissions(
        admin=Permissions.ALL, team_member={"po_name", "po_email", "contact_email"}
    )

    def update_team(self, team_id, *, data: dict, scopes: list[str]) -> Team:
        self.auth.permit(self.UPDATE_TEAM_PERMISSION, scopes=scopes, fields=data.keys())
        if int(data.get("id", team_id)) != int(team_id):
            raise exceptions.IllegalOperation("Cannot update product id")
        team = self.get_team(team_id)
        team.update_from_dict(data)
        return self._persist(team)

    def delete_team(self, team_id, *, scopes) -> None:
        self.auth.require(role=Role.ADMIN, scopes=scopes)
        return self.repository.delete(team_id)

    def _persist(self, team: Team) -> None:
        return self.repository.save(team)
