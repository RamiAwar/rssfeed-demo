class BaseError(Exception):
    def __init__(self, message: str):
        self.message = message


class ValidationError(BaseError):
    ...


class NotFoundError(BaseError):
    ...
