"""
Tests for database models and data structures.

Tests cover:
- Model validation and constraints
- Data serialization and deserialization
- Enum value handling
- Model relationships and dependencies
"""

import pytest
from datetime import datetime, timedelta
from dataclasses import asdict

from src.database.models import (
    EmailProcessingState, ProcessingStatus, EmailMetadata,
    AuditLogEntry, AuditAction, DatabaseConnectionConfig,
    ConnectionPoolStats, ConnectionHealth, FailoverStatus,
    QueryMetrics
)


class TestEmailMetadata:
    """Test suite for EmailMetadata model."""
    
    def test_email_metadata_creation_valid(self):
        """Test creating valid email metadata."""
        metadata = EmailMetadata(
            uid="test-uid-123",
            message_id="<test@example.com>",
            sender="sender@example.com",
            subject="Test Email",
            received_date=datetime.utcnow(),
            account_id="test-account",
            content_hash="abc123def456",
            attachment_count=2,
            size_bytes=1024
        )
        
        assert metadata.uid == "test-uid-123"
        assert metadata.message_id == "<test@example.com>"
        assert metadata.sender == "sender@example.com"
        assert metadata.subject == "Test Email"
        assert metadata.account_id == "test-account"
        assert metadata.content_hash == "abc123def456"
        assert metadata.attachment_count == 2
        assert metadata.size_bytes == 1024
    
    def test_email_metadata_validation_empty_uid(self):
        """Test validation fails for empty UID."""
        with pytest.raises(ValueError, match="Email UID cannot be empty"):
            EmailMetadata(
                uid="",
                message_id="<test@example.com>",
                sender="sender@example.com",
                subject="Test Email",
                received_date=datetime.utcnow(),
                account_id="test-account"
            )


class TestEmailProcessingState:
    """Test suite for EmailProcessingState model."""
    
    def test_email_processing_state_creation(self):
        """Test creating email processing state."""
        metadata = EmailMetadata(
            uid="test-uid-123",
            message_id="<test@example.com>",
            sender="sender@example.com",
            subject="Test Email",
            received_date=datetime.utcnow(),
            account_id="test-account"
        )
        
        state = EmailProcessingState(
            email_uid="test-uid-123",
            message_id="<test@example.com>",
            account_id="test-account",
            status=ProcessingStatus.DETECTED,
            metadata=metadata,
            classification_result={"type": "NEW_EO", "confidence": 0.95}
        )
        
        assert state.email_uid == "test-uid-123"
        assert state.message_id == "<test@example.com>"
        assert state.account_id == "test-account"
        assert state.status == ProcessingStatus.DETECTED
        assert state.metadata == metadata
        assert state.classification_result == {"type": "NEW_EO", "confidence": 0.95}
        assert state.retry_count == 0
        assert state.created_at is not None
        assert state.updated_at is not None
        assert state.processed_at is None


class TestAuditLogEntry:
    """Test suite for AuditLogEntry model."""
    
    def test_audit_log_entry_creation(self):
        """Test creating audit log entry."""
        entry = AuditLogEntry(
            component="email-processor",
            action=AuditAction.EMAIL_DETECTED,
            details={"email_uid": "test-123", "sender": "test@example.com"},
            email_uid="test-123",
            account_id="test-account",
            user_id="user-123",
            security_classification="CONFIDENTIAL"
        )
        
        assert entry.component == "email-processor"
        assert entry.action == AuditAction.EMAIL_DETECTED
        assert entry.details == {"email_uid": "test-123", "sender": "test@example.com"}
        assert entry.email_uid == "test-123"
        assert entry.account_id == "test-account"
        assert entry.user_id == "user-123"
        assert entry.security_classification == "CONFIDENTIAL"
        assert entry.entry_id is not None
        assert entry.timestamp is not None
        assert isinstance(entry.timestamp, datetime)


class TestDatabaseConnectionConfig:
    """Test suite for DatabaseConnectionConfig model."""
    
    def test_database_connection_config_creation(self):
        """Test creating database connection configuration."""
        config = DatabaseConnectionConfig(
            primary_host="primary-db.example.com",
            primary_port=5432,
            backup_host="backup-db.example.com",
            backup_port=5433,
            database="email_agent",
            username="db_user",
            password="db_password",
            pool_size=10,
            max_overflow=20
        )
        
        assert config.primary_host == "primary-db.example.com"
        assert config.primary_port == 5432
        assert config.backup_host == "backup-db.example.com"
        assert config.backup_port == 5433
        assert config.database == "email_agent"
        assert config.username == "db_user"
        assert config.password == "db_password"
        assert config.pool_size == 10
        assert config.max_overflow == 20


class TestEnums:
    """Test suite for enum values."""
    
    def test_processing_status_enum_values(self):
        """Test ProcessingStatus enum values."""
        assert ProcessingStatus.DETECTED.value == "detected"
        assert ProcessingStatus.PROCESSING.value == "processing"
        assert ProcessingStatus.CLASSIFIED.value == "classified"
        assert ProcessingStatus.PUBLISHED.value == "published"
        assert ProcessingStatus.COMPLETED.value == "completed"
        assert ProcessingStatus.FAILED.value == "failed"
        assert ProcessingStatus.QUARANTINED.value == "quarantined"
    
    def test_audit_action_enum_values(self):
        """Test AuditAction enum values."""
        assert AuditAction.EMAIL_DETECTED.value == "email_detected"
        assert AuditAction.EMAIL_PROCESSED.value == "email_processed"
        assert AuditAction.EMAIL_CLASSIFIED.value == "email_classified"
        assert AuditAction.EVENT_PUBLISHED.value == "event_published"
        assert AuditAction.SECURITY_VALIDATION.value == "security_validation"
        assert AuditAction.CREDENTIAL_ACCESS.value == "credential_access"
        assert AuditAction.SYSTEM_ERROR.value == "system_error"
        assert AuditAction.FAILOVER_TRIGGERED.value == "failover_triggered"
        assert AuditAction.CONNECTION_ESTABLISHED.value == "connection_established"
        assert AuditAction.CONNECTION_FAILED.value == "connection_failed"