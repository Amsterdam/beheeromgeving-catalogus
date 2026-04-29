from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from domain.auth import AuthorizationService, ProductId, Scope


class ProductReadLevel(Enum):
    FULL = auto()
    INTERNAL = auto()
    PUBLISHED = auto()


@dataclass(frozen=True)
class ProductReadPolicy:
    auth: AuthorizationService

    def level(self, *, scopes: list[Scope] | None) -> ProductReadLevel:
        if scopes is None:
            return ProductReadLevel.PUBLISHED
        if self.auth.is_admin(scopes=scopes):
            return ProductReadLevel.FULL
        if self.auth.is_employee(scopes=scopes):
            return ProductReadLevel.INTERNAL
        return ProductReadLevel.PUBLISHED

    def level_for_product(
        self, *, product_id: ProductId, scopes: list[Scope] | None
    ) -> ProductReadLevel:
        if scopes is None:
            return ProductReadLevel.PUBLISHED
        if self.auth.is_admin(scopes=scopes) or self.auth.is_team_member_of_product(
            product_id=product_id, scopes=scopes
        ):
            return ProductReadLevel.FULL

        if self.auth.is_employee(scopes=scopes):
            return ProductReadLevel.INTERNAL

        return ProductReadLevel.PUBLISHED

    def level_for_product_name(self, *, name: str, scopes: list[Scope] | None) -> ProductReadLevel:
        if scopes is None:
            return ProductReadLevel.PUBLISHED
        if self.auth.is_admin(scopes=scopes) or self.auth.is_team_member_of_product_name(
            name=name, scopes=scopes
        ):
            return ProductReadLevel.FULL
        return ProductReadLevel.PUBLISHED
