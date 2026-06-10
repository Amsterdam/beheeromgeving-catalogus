from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from domain import exceptions
from domain.base import BaseObject
from domain.team import Team


@dataclass
class PublishableObject(BaseObject):
    publication_status: str | None = None
    publication_date: datetime | None = None


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


def test_update_from_dict_does_not_update_publication_date_on_second_publish():
    first_publication_date = datetime(2024, 1, 1, tzinfo=UTC)
    publishable = PublishableObject(
        publication_status="P",
        publication_date=first_publication_date,
    )

    publishable.update_from_dict({"publication_status": "P"})

    assert publishable.publication_date == first_publication_date
