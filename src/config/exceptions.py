"""
Configuration-related exceptions for the Email Agent system.
"""


class ConfigurationError(Exception):
    """Base exception for configuration-related errors."""
    pass


class ValidationError(ConfigurationError):
    """Raised when configuration validation fails."""
    pass


class EnvironmentError(ConfigurationError):
    """Raised when environment-specific configuration issues occur."""
    pass


class SchemaError(ConfigurationError):
    """Raised when configuration schema validation fails."""
    pass


class ReloadError(ConfigurationError):
    """Raised when configuration hot reload fails."""
    pass