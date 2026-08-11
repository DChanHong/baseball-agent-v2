class AuthConfigurationError(RuntimeError):
    """Raised when required Supabase Auth settings are missing."""


class UnauthenticatedError(RuntimeError):
    """Raised when a request does not have a valid authenticated session."""
