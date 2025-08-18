"""
Security-related exceptions for the Email Agent system.
"""


class SecurityError(Exception):
    """Base exception for security-related errors."""
    pass


class EncryptionError(SecurityError):
    """Exception raised when encryption operations fail."""
    pass


class DecryptionError(SecurityError):
    """Exception raised when decryption operations fail."""
    pass


class CredentialError(SecurityError):
    """Exception raised for credential-related errors."""
    pass


class RotationError(SecurityError):
    """Exception raised when credential rotation fails."""
    pass


class ValidationError(SecurityError):
    """Exception raised when security validation fails."""
    pass


class KeyDerivationError(SecurityError):
    """Exception raised when key derivation fails."""
    pass


class StrengthValidationError(ValidationError):
    """Exception raised when credential strength validation fails."""
    pass


class EmailSecurityError(SecurityError):
    """Exception raised for email security validation errors."""
    pass


class SenderAuthorizationError(EmailSecurityError):
    """Exception raised when sender authorization fails."""
    pass


class AttachmentThreatError(EmailSecurityError):
    """Exception raised when malicious attachments are detected."""
    pass


class ContentThreatError(EmailSecurityError):
    """Exception raised when malicious content is detected."""
    pass


class DigitalSignatureError(EmailSecurityError):
    """Exception raised when digital signature verification fails."""
    pass


class QuarantineError(EmailSecurityError):
    """Exception raised when email quarantine operations fail."""
    pass