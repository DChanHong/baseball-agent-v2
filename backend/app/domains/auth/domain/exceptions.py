class AuthConfigurationError(RuntimeError):
    """Raised when required Supabase Auth settings are missing."""


class UnauthenticatedError(RuntimeError):
    """Raised when a request does not have a valid authenticated session."""


class InvalidProfileUpdateError(ValueError):
    """Raised when a requested application profile update is invalid."""
