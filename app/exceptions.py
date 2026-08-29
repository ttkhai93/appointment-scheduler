class DomainError(Exception):
    """Base class for expected, user-facing domain errors."""


class NotFoundError(DomainError):
    """A referenced entity does not exist."""


class DomainValidationError(DomainError):
    """The request violates a domain rule (grid, business hours, ...)."""


class BookingConflictError(DomainError):
    """Booking could not be confirmed because resources are unavailable."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
