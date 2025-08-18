"""
Enhanced Database Interface with Audit Logging for Email Agent.

This module provides federal-grade database operations with:
- Connection pooling for high availability
- Immutable audit logging with cryptographic signing
- Email processing state tracking
- Automatic failover capabilities
- Comprehensive error handling and recovery
"""

from .manager import DatabaseManager
from .audit import AuditLogger
from .models import (
    EmailProcessingState, AuditLogEntry, ProcessingStatus,
    EmailMetadata, ConnectionHealth, FailoverStatus
)
from .exceptions import (
    DatabaseError, ConnectionError, AuditError,
    FailoverError, StateTrackingError
)

__all__ = [
    'DatabaseManager',
    'AuditLogger', 
    'EmailProcessingState',
    'AuditLogEntry',
    'ProcessingStatus',
    'EmailMetadata',
    'ConnectionHealth',
    'FailoverStatus',
    'DatabaseError',
    'ConnectionError',
    'AuditError',
    'FailoverError',
    'StateTrackingError'
]