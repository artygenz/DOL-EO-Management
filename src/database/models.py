"""
Database models for email processing state tracking and audit logging.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum
import uuid


class ProcessingStatus(Enum):
    """Email processing status enumeration."""
    DETECTED = "detected"
    PROCESSING = "processing"
    CLASSIFIED = "classified"
    PUBLISHED = "published"
    COMPLETED = "completed"
    FAILED = "failed"
    QUARANTINED = "quarantined"


class AuditAction(Enum):
    """Audit log action types."""
    EMAIL_DETECTED = "email_detected"
    EMAIL_PROCESSED = "email_processed"
    EMAIL_CLASSIFIED = "email_classified"
    EVENT_PUBLISHED = "event_published"
    SECURITY_VALIDATION = "security_validation"
    CREDENTIAL_ACCESS = "credential_access"
    SYSTEM_ERROR = "system_error"
    FAILOVER_TRIGGERED = "failover_triggered"
    CONNECTION_ESTABLISHED = "connection_established"
    CONNECTION_FAILED = "connection_failed"


class ConnectionHealth(Enum):
    """Database connection health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    RECOVERING = "recovering"


class FailoverStatus(Enum):
    """Database failover status."""
    PRIMARY_ACTIVE = "primary_active"
    BACKUP_ACTIVE = "backup_active"
    FAILOVER_IN_PROGRESS = "failover_in_progress"
    BOTH_FAILED = "both_failed"


@dataclass
class EmailMetadata:
    """Email metadata for database storage."""
    uid: str
    message_id: str
    sender: str
    subject: str
    received_date: datetime
    account_id: str
    thread_id: Optional[str] = None
    content_hash: Optional[str] = None
    attachment_count: int = 0
    size_bytes: int = 0
    
    def __post_init__(self):
        """Validate email metadata after initialization."""
        if not self.uid:
            raise ValueError("Email UID cannot be empty")
        if not self.message_id:
            raise ValueError("Message ID cannot be empty")
        if not self.sender:
            raise ValueError("Sender cannot be empty")
        if not self.account_id:
            raise ValueError("Account ID cannot be empty")


@dataclass
class EmailProcessingState:
    """Email processing state tracking model."""
    id: Optional[int] = None
    email_uid: str = ""
    message_id: str = ""
    account_id: str = ""
    status: ProcessingStatus = ProcessingStatus.DETECTED
    metadata: Optional[EmailMetadata] = None
    classification_result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Set default timestamps if not provided."""
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()
    
    def update_status(self, new_status: ProcessingStatus, error_message: Optional[str] = None):
        """Update processing status with timestamp."""
        self.status = new_status
        self.updated_at = datetime.utcnow()
        if error_message:
            self.error_message = error_message
        if new_status == ProcessingStatus.COMPLETED:
            self.processed_at = datetime.utcnow()


@dataclass
class AuditLogEntry:
    """Immutable audit log entry with cryptographic signing."""
    id: Optional[int] = None
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    component: str = ""
    action: AuditAction = AuditAction.SYSTEM_ERROR
    email_uid: Optional[str] = None
    account_id: Optional[str] = None
    user_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    security_classification: str = "UNCLASSIFIED"
    digital_signature: Optional[str] = None
    hash_chain_previous: Optional[str] = None
    hash_chain_current: Optional[str] = None
    
    def __post_init__(self):
        """Validate audit log entry after initialization."""
        if not self.component:
            raise ValueError("Component cannot be empty")
        if not isinstance(self.details, dict):
            raise ValueError("Details must be a dictionary")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert audit entry to dictionary for hashing."""
        return {
            'entry_id': self.entry_id,
            'timestamp': self.timestamp.isoformat(),
            'component': self.component,
            'action': self.action.value,
            'email_uid': self.email_uid,
            'account_id': self.account_id,
            'user_id': self.user_id,
            'details': self.details,
            'security_classification': self.security_classification,
            'hash_chain_previous': self.hash_chain_previous
        }


@dataclass
class DatabaseConnectionConfig:
    """Database connection configuration with failover support."""
    primary_host: str
    primary_port: int = 5432
    backup_host: Optional[str] = None
    backup_port: int = 5432
    database: str = "email_agent"
    username: str = ""
    password: str = ""
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600
    ssl_mode: str = "require"
    connection_timeout: int = 10
    query_timeout: int = 30
    retry_attempts: int = 3
    retry_delay: int = 5
    
    def __post_init__(self):
        """Validate database connection configuration."""
        if not self.primary_host:
            raise ValueError("Primary database host cannot be empty")
        if not self.database:
            raise ValueError("Database name cannot be empty")
        if not self.username:
            raise ValueError("Database username cannot be empty")
        if self.pool_size <= 0:
            raise ValueError("Pool size must be positive")
        if self.max_overflow < 0:
            raise ValueError("Max overflow cannot be negative")


@dataclass
class ConnectionPoolStats:
    """Connection pool statistics."""
    pool_size: int
    checked_out: int
    overflow: int
    checked_in: int
    total_connections: int
    failed_connections: int
    health_status: ConnectionHealth
    last_health_check: datetime
    
    @property
    def utilization_percent(self) -> float:
        """Calculate pool utilization percentage."""
        if self.pool_size == 0:
            return 0.0
        return (self.checked_out / self.pool_size) * 100.0
    
    @property
    def is_healthy(self) -> bool:
        """Check if pool is in healthy state."""
        return self.health_status == ConnectionHealth.HEALTHY


@dataclass
class QueryMetrics:
    """Database query performance metrics."""
    query_type: str
    execution_time_ms: float
    rows_affected: int
    timestamp: datetime = field(default_factory=datetime.utcnow)
    success: bool = True
    error_message: Optional[str] = None
    
    def __post_init__(self):
        """Validate query metrics."""
        if self.execution_time_ms < 0:
            raise ValueError("Execution time cannot be negative")
        if self.rows_affected < 0:
            raise ValueError("Rows affected cannot be negative")