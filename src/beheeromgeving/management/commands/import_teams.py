import json
from pathlib import Path

import requests
from django.conf import settings
from django.core.management import BaseCommand

from api.datatransferobjects import Team
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
        # NOTE: This file is not committed to the repo, as it contains names and emails.
        # It will be available in a private repo.
        with open(Path(__file__).parent / "productowners.json") as f:
            po_json = json.load(f)

            for acronym, data in publishers.items():
                if acronym not in po_json:
                    print(f"{acronym} isn't available. {data['name']}")
                    continue
                po_name = po_json[acronym]["po_name"]
                po_email = po_json[acronym]["po_email"]
                contact_email = "contact@amsterdam.nl"
                team = Team(
                    name=data["name"],
                    acronym=acronym,
                    scope=f"publisher-p-{acronym.lower()}",
                    po_name=po_name,
                    po_email=po_email,
                    contact_email=contact_email,
                )
                try:
                    self.service.create_team(
                        data=team.model_dump(), scopes=[settings.ADMIN_ROLE_NAME]
                    )
                except ValidationError as e:
                    print(e.message)
                    continue
