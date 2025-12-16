SEPARATORS = ["_", " ", ";", ","]


def fix_distribution_format(apps, schema_editor):
    Distribution = apps.get_model("beheeromgeving", "Distribution")
    for distribution in Distribution.objects.all():
        for sep in SEPARATORS:
            if distribution.format is not None and sep in distribution.format:
                distribution.format = distribution.format.split(sep)[0]
                distribution.save()


def update_team_scopes(apps, schema_editor):
    Team = apps.get_model("beheeromgeving", "Team")
    for team in Team.objects.all():
        team.scope = f"publisher.{team.acronym}"
        team.save()


def revert_team_scopes(apps, schema_editor):
    Team = apps.get_model("beheeromgeving", "Team")
    for team in Team.objects.all():
        team.scope = f"publisher-p-{team.acronym.lower()}"
        team.save()
