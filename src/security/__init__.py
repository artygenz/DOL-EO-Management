"""
Security module for the Email Agent system.
Provides federal-grade security controls including credential management,
encryption utilities, and compliance validation.
"""

from .credential_manager import CredentialManager
from .exceptions import (
    SecurityError, EncryptionError, DecryptionError, 
    CredentialError, RotationError, ValidationError
)

__all__ = [
    'CredentialManager',
    'SecurityError',
    'EncryptionError', 
    'DecryptionError',
    'CredentialError',
    'RotationError',
    'ValidationError'
]