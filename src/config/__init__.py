"""
Configuration management module for the Email Agent system.
Provides environment-specific configuration loading, validation, and hot reloading.
"""

from .manager import ConfigurationManager
from .models import (
    EmailAccountConfig,
    IMAPSettings,
    SMTPSettings,
    SecuritySettings,
    DatabaseConfig,
    RedisConfig,
    MonitoringConfig,
    SystemConfig
)
from .validators import ConfigurationValidator
from .exceptions import (
    ConfigurationError,
    ValidationError,
    EnvironmentError,
    SchemaError
)

__all__ = [
    'ConfigurationManager',
    'EmailAccountConfig',
    'IMAPSettings', 
    'SMTPSettings',
    'SecuritySettings',
    'DatabaseConfig',
    'RedisConfig',
    'MonitoringConfig',
    'SystemConfig',
    'ConfigurationValidator',
    'ConfigurationError',
    'ValidationError',
    'EnvironmentError',
    'SchemaError'
]