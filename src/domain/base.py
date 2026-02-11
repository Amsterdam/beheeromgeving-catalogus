import abc
from dataclasses import asdict, dataclass
from typing import Any


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

    def update_from_dict(self, data: dict):
        for k, v in data.items():
            setattr(self, k, v)


# alias for typing
list_ = list


class AbstractRepository[T](abc.ABC):
    @abc.abstractmethod
    def get(self, id: int) -> T:
        raise NotImplementedError

    def get_published(self, id: int) -> T:
        raise NotImplementedError

    @abc.abstractmethod
    def get_by_name(self, name: str) -> T:
        raise NotImplementedError

    def get_published_by_name(self, name: str) -> T:
        raise NotImplementedError

    @abc.abstractmethod
    def list(self) -> list_[T]:
        raise NotImplementedError

    @abc.abstractmethod
    def save(self, item: T) -> T:
        raise NotImplementedError

    @abc.abstractmethod
    def delete(self, id: int) -> int:
        raise NotImplementedError


class AbstractAuthRepository(abc.ABC):
    @abc.abstractmethod
    def get_config(self):
        raise NotImplementedError

    @abc.abstractmethod
    def refresh_from_db(self) -> None:
        raise NotImplementedError


class AbstractService:
    pass
