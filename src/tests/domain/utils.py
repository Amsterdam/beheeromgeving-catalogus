from domain import exceptions, objects
from domain.repositories import AbstractRepository


class DummyRepository(AbstractRepository):
    _items: dict[int, objects.BaseObject] = {}

    def __init__(self, objects: list[objects.BaseObject]):
        for object in objects:
            self._items[object.id] = object

    def get(self, id):
        try:
            return self._items[id]
        except KeyError as e:
            raise exceptions.ObjectDoesNotExist(f"Object with id {id} does not exist") from e

    def list(self):
        return list(self._items.values())

    def save(self, object: objects.BaseObject):
        object.id = object.id or max(self._items.keys()) if len(self._items.keys()) else 0
        self._items[object.id] = object
        return object

    def delete(self, id):
        try:
            self._items.pop(id)
        except KeyError as e:
            raise exceptions.ObjectDoesNotExist(f"Object with id {id} does not exist") from e
