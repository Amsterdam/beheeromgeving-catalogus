import abc
from dataclasses import asdict, dataclass, fields
from datetime import UTC, datetime
from typing import Any

from domain import exceptions


@dataclass
class BaseObject:
    """The Base Object from which all domain objects inherit."""

    def items(self) -> dict[str, Any]:
        """Returns a dictionary that can be persisted in the ORM, omitting fields
        that need their own logic."""
        dictionary = asdict(self)
        for key in getattr(self, "_skip_keys", set()) | {"_skip_keys"}:
            if key in dictionary:
                dictionary.pop(key)
        return dictionary

    def update_from_dict(self, data: dict[str, Any]):
        allowed_keys = {f.name for f in fields(self)}
        unknown_keys = set(data).difference(allowed_keys)
        if unknown_keys:
            unknown_keys_str = ", ".join(sorted(unknown_keys))
            raise exceptions.ValidationError(
                f"Unknown fields for {type(self).__name__}: {unknown_keys_str}"
            )

        for k, v in data.items():
            setattr(self, k, v)
            # when published, set the publication_date.
            if k == "publication_status" and v == "P":
                self.publication_date = datetime.now(tz=UTC)


# alias for typing
list_ = list


class AbstractRepository[T](abc.ABC):
    @abc.abstractmethod
    def get(self, id: int) -> T:
        raise NotImplementedError

    def get_for_publication_status(self, id: int, allowed_statuses: list_[Any]) -> T:
        raise NotImplementedError

    @abc.abstractmethod
    def get_by_name(self, name: str) -> T:
        raise NotImplementedError

    def get_for_publication_status_by_name(self, name: str, allowed_statuses: list_[Any]) -> T:
        raise NotImplementedError

    def list(self) -> list_:
        raise NotImplementedError

    def list_for_publication_status(self, allowed_statuses: list_[Any]) -> list_:
        raise NotImplementedError

    def list_all(self) -> list_[T]:
        raise NotImplementedError

    def list_mine(self, *, query, filter, order, teams) -> list_:
        raise NotImplementedError

    @abc.abstractmethod
    def save(self, item: T) -> T:
        raise NotImplementedError

    def get_draft(self, id: int) -> T:
        raise NotImplementedError

    def save_draft(self, item: T) -> T:
        raise NotImplementedError

    def publish_draft(self, id: int) -> T:
        raise NotImplementedError

    def delete_draft(self, id: int) -> int:
        raise NotImplementedError

    def get_contract_draft(self, *, product_id: int, contract_id: int) -> Any:
        raise NotImplementedError

    def save_contract_draft(self, *, product_id: int, contract: Any) -> Any:
        raise NotImplementedError

    def delete_contract_draft(self, *, product_id: int, contract_id: int) -> int:
        raise NotImplementedError

    @abc.abstractmethod
    def delete(self, id: int) -> int:
        raise NotImplementedError


class AbstractAuthRepository(abc.ABC):
    feature_enabled: bool
    admin_role: str
    employee_role: str

    @abc.abstractmethod
    def can_access_team(self, team_id: int, scopes: list[Any]) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def can_access_product(self, product_id: int, scopes: list[Any]) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def can_access_product_name(self, name: str, scopes: list[Any]) -> bool:
        raise NotImplementedError


class AbstractService:
    pass
