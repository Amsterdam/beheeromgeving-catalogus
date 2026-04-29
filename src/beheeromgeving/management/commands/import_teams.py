import requests
from django.conf import settings
from django.core.management import BaseCommand

from api.datatransferobjects import TeamCreate
from domain.auth import AuthorizationRepository, AuthorizationService, authorize
from domain.exceptions import ValidationError
from domain.team import TeamRepository, TeamService


class Command(BaseCommand):
    def __init__(self):
        self.service = TeamService(TeamRepository())
        authorize.set_auth_service(AuthorizationService(AuthorizationRepository()))

    def add_arguments(self, parser):
        parser.add_argument(
            "--purge",
            default=False,
            help="Remove teams",
            dest="purge",
            action="store_true",
        )

        return super().add_arguments(parser)

    def handle(self, *args, **options):
        if options.get("purge", False):
            all_teams = self.service.get_teams()
            for team in all_teams:
                print(f"deleting team: {team.acronym}")
                if team.id is not None:
                    self.service.delete_team(team.id, scopes=[settings.ADMIN_ROLE_NAME])
            return
        publisher_acronyms = requests.get(
            "https://schemas.data.amsterdam.nl/publishers/index", timeout=10
        ).json()
        publishers = {}
        for acronym in publisher_acronyms:
            print(f"fetching {acronym}")
            pub = requests.get(
                f"https://schemas.data.amsterdam.nl/publishers/{acronym}", timeout=10
            ).json()
            publishers[acronym] = pub

        for acronym, data in publishers.items():
            team = TeamCreate(
                name=data["name"],
                acronym=acronym,
                scope=f"publisher-p-{acronym.lower()}",
                po_name=f"PO team {acronym}",
                po_email=f"team.{acronym.lower()}@amsterdam.nl",
                contact_email="contact@amsterdam.nl",
            )
            try:
                self.service.create_team(data=team.model_dump(), scopes=[settings.ADMIN_ROLE_NAME])
            except ValidationError as e:
                print(e.message)
                continue
