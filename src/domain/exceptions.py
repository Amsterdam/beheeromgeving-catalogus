class DomainException(Exception):
    message: str

    def __init__(self, message: str = ""):
        self.message = message


class ObjectDoesNotExist(DomainException):
    pass


class IllegalOperation(DomainException):
    pass


class ValidationError(DomainException):
    pass


class NotAuthorized(DomainException):
    pass
