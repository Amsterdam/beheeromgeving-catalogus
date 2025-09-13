from domain import exceptions
from domain.auth import Permission, Role, authorize
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
        authorize.register_auth(
            "is_admin",
            method=self.auth.permit,
            permission=Permission(role=Role.ADMIN, allowed_fields=Permission.ALL),
        )
        authorize.register_auth(
            "can_update_team",
            method=self.auth.permit,
            permission=Permission(
                role=Role.TEAM_MEMBER, allowed_fields={"po_name", "po_email", "contact_email"}
            ),
        )

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

    @authorize("is_admin", "can_update_team")
    def update_team(self, team_id: int, **kwargs) -> Team:
        data = kwargs.get("data", {})
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
