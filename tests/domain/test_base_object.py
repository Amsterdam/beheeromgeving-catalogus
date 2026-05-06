import pytest

from domain import exceptions
from domain.team import Team


def test_update_from_dict_rejects_unknown_keys():
    team = Team(
        id=1,
        name="Team",
        description="Desc",
        acronym="T",
        po_name="PO",
        po_email="po@example.com",
        contact_email="contact@example.com",
        scope="scope_team",
    )

    with pytest.raises(exceptions.ValidationError):
        team.update_from_dict({"unknown_field": "nope"})


def test_update_from_dict_accepts_known_keys():
    team = Team(
        id=1,
        name="Team",
        description="Desc",
        acronym="T",
        po_name="PO",
        po_email="po@example.com",
        contact_email="contact@example.com",
        scope="scope_team",
    )

    team.update_from_dict({"description": "New description"})
    assert team.description == "New description"
