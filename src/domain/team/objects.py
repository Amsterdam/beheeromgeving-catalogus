from dataclasses import dataclass

from domain.base import BaseObject


@dataclass
class Team(BaseObject):
    name: str
    description: str
    acronym: str
    po_name: str
    po_email: str
    contact_email: str
    scope: str
    id: int | None = None
    product_count: int = 0

    _skip_keys = {"product_count"}
