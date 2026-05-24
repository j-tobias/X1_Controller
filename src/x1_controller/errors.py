"""Exceptions for the Gira X1 controller."""


class GiraControllerError(Exception):
    """Base exception for GiraController errors."""
    pass


class AuthenticationError(GiraControllerError):
    """Raised when authentication fails."""
    pass


class GiraConnectionError(GiraControllerError):
    """Raised when connection to X1 fails."""
    pass
