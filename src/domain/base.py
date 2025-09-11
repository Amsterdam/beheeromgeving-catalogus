import abc


class AbstractRepository(abc.ABC):
    @abc.abstractmethod
    def get(self, ref):
        raise NotImplementedError

    @abc.abstractmethod
    def list(self):
        raise NotImplementedError

    @abc.abstractmethod
    def save(self, ref, data):
        raise NotImplementedError

    @abc.abstractmethod
    def delete(self, ref):
        raise NotImplementedError


class AbstractProductRepository(AbstractRepository):
    pass


class AbstractTeamRepository(AbstractRepository):
    pass


class AbstractAuthRepository(abc.ABC):
    @abc.abstractmethod
    def get_config(self):
        raise NotImplementedError


class AbstractService:
    pass
