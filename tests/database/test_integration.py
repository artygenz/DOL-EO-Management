"""
Integration tests for database functionality.

These tests focus on the core functionality without complex mocking.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock

from src.database.models import (
    EmailProcessingState, ProcessingStatus, EmailMetadata,
    AuditLogEntry, AuditAction, DatabaseConnectionConfig,
    ConnectionPoolStats, ConnectionHealth, QueryMetrics
)
from src.database.exceptions import DatabaseError, AuditError


class TestDatabaseModelsIntegration:
    """Integration tests for database models."""
    
    def test_email_processing_state_lifecycle(self):
        """Test complete email processing state lifecycle."""
        # Create metadata
        metadata = EmailMetadata(
            uid="test-uid-123",
            message_id="<test@example.com>",
            sender="sender@example.com",
            subject="Test Email",
            received_date=datetime.utcnow(),
            account_id="test-account",
            content_hash="abc123def456"
        )
        
        # Create initial state
        state = EmailProcessingState(
            email_uid="test-uid-123",
            message_id="<test@example.com>",
            account_id="test-account",
            status=ProcessingStatus.DETECTED,
            metadata=metadata
        )
        
        assert state.status == ProcessingStatus.DETECTED
        assert state.processed_at is None
        
        # Update to processing
        state.update_status(ProcessingStatus.PROCESSING)
        assert state.status == ProcessingStatus.PROCESSING
        
        # Update to completed
        state.update_status(ProcessingStatus.COMPLETED)
        assert state.status == ProcessingStatus.COMPLETED
        assert state.processed_at is not None
    
    def test_audit_log_entry_creation_and_serialization(self):
        """Test audit log entry creation and serialization."""
        entry = AuditLogEntry(
            component="email-processor",
            action=AuditAction.EMAIL_DETECTED,
            details={"email_uid": "test-123", "classification": "NEW_EO"},
            email_uid="test-123",
            account_id="test-account"
        )
        
        # Test basic properties
        assert entry.component == "email-processor"
        assert entry.action == AuditAction.EMAIL_DETECTED
        assert entry.email_uid == "test-123"
        assert entry.entry_id is not None
        assert entry.timestamp is not None
        
        # Test serialization
        entry_dict = entry.to_dict()
        assert isinstance(entry_dict, dict)
        assert entry_dict['component'] == "email-processor"
        assert entry_dict['action'] == "email_detected"
        assert entry_dict['details'] == {"email_uid": "test-123", "classification": "NEW_EO"}
    
    def test_database_connection_config_validation(self):
        """Test database connection configuration validation."""
        # Valid configuration
        config = DatabaseConnectionConfig(
            primary_host="localhost",
            database="test_db",
            username="test_user",
            password="test_pass"
        )
        
        assert config.primary_host == "localhost"
        assert config.database == "test_db"
        assert config.pool_size == 10  # Default value
        
        # Test validation errors
        with pytest.raises(ValueError, match="Primary database host cannot be empty"):
            DatabaseConnectionConfig(
                primary_host="",
                database="test_db",
                username="test_user",
                password="test_pass"
            )
    
    def test_connection_pool_stats_calculations(self):
        """Test connection pool statistics calculations."""
        stats = ConnectionPoolStats(
            pool_size=10,
            checked_out=7,
            overflow=2,
            checked_in=3,
            total_connections=12,
            failed_connections=1,
            health_status=ConnectionHealth.HEALTHY,
            last_health_check=datetime.utcnow()
        )
        
        # Test utilization calculation
        assert stats.utilization_percent == 70.0
        assert stats.is_healthy is True
        
        # Test with degraded health
        degraded_stats = ConnectionPoolStats(
            pool_size=10,
            checked_out=5,
            overflow=0,
            checked_in=5,
            total_connections=10,
            failed_connections=3,
            health_status=ConnectionHealth.DEGRADED,
            last_health_check=datetime.utcnow()
        )
        
        assert degraded_stats.is_healthy is False
    
    def test_query_metrics_validation(self):
        """Test query metrics validation."""
        # Valid metrics
        metrics = QueryMetrics(
            query_type="SELECT",
            execution_time_ms=150.5,
            rows_affected=10
        )
        
        assert metrics.query_type == "SELECT"
        assert metrics.execution_time_ms == 150.5
        assert metrics.rows_affected == 10
        assert metrics.success is True
        
        # Test validation errors
        with pytest.raises(ValueError, match="Execution time cannot be negative"):
            QueryMetrics(
                query_type="SELECT",
                execution_time_ms=-10.0,
                rows_affected=5
            )
        
        with pytest.raises(ValueError, match="Rows affected cannot be negative"):
            QueryMetrics(
                query_type="INSERT",
                execution_time_ms=100.0,
                rows_affected=-1
            )


class TestAuditLoggerIntegration:
    """Integration tests for audit logger functionality."""
    
    def test_audit_entry_hash_consistency(self):
        """Test that audit entry hashing is consistent."""
        from src.database.audit import AuditLogger
        import tempfile
        import os
        
        with tempfile.TemporaryDirectory() as temp_dir:
            key_path = os.path.join(temp_dir, 'test_key.pem')
            logger = AuditLogger(key_path, None)
            
            entry = AuditLogEntry(
                component="test-component",
                action=AuditAction.EMAIL_DETECTED,
                details={"test": "data", "number": 123},
                email_uid="test-123"
            )
            
            # Calculate hash multiple times
            hash1 = logger._calculate_entry_hash(entry)
            hash2 = logger._calculate_entry_hash(entry)
            
            assert hash1 == hash2
            assert len(hash1) == 64  # SHA-256 hex digest length
    
    def test_audit_entry_signature_verification(self):
        """Test audit entry signature creation and verification."""
        from src.database.audit import AuditLogger
        import tempfile
        import os
        
        with tempfile.TemporaryDirectory() as temp_dir:
            key_path = os.path.join(temp_dir, 'test_key.pem')
            logger = AuditLogger(key_path, None)
            
            entry = AuditLogEntry(
                component="test-component",
                action=AuditAction.EMAIL_DETECTED,
                details={"test": "data"},
                hash_chain_current="test-hash"
            )
            
            # Sign the entry
            signature = logger._sign_entry(entry)
            entry.digital_signature = signature
            
            # Verify signature
            is_valid = logger._verify_signature(entry)
            assert is_valid is True
            
            # Test with tampered signature
            entry.digital_signature = "tampered_signature"
            is_valid = logger._verify_signature(entry)
            assert is_valid is False


class TestDatabaseErrorHandling:
    """Test database error handling scenarios."""
    
    def test_email_metadata_validation_errors(self):
        """Test email metadata validation error scenarios."""
        # Test empty UID
        with pytest.raises(ValueError, match="Email UID cannot be empty"):
            EmailMetadata(
                uid="",
                message_id="<test@example.com>",
                sender="sender@example.com",
                subject="Test Email",
                received_date=datetime.utcnow(),
                account_id="test-account"
            )
        
        # Test empty message ID
        with pytest.raises(ValueError, match="Message ID cannot be empty"):
            EmailMetadata(
                uid="test-uid-123",
                message_id="",
                sender="sender@example.com",
                subject="Test Email",
                received_date=datetime.utcnow(),
                account_id="test-account"
            )
        
        # Test empty sender
        with pytest.raises(ValueError, match="Sender cannot be empty"):
            EmailMetadata(
                uid="test-uid-123",
                message_id="<test@example.com>",
                sender="",
                subject="Test Email",
                received_date=datetime.utcnow(),
                account_id="test-account"
            )
    
    def test_audit_log_entry_validation_errors(self):
        """Test audit log entry validation error scenarios."""
        # Test empty component
        with pytest.raises(ValueError, match="Component cannot be empty"):
            AuditLogEntry(
                component="",
                action=AuditAction.EMAIL_DETECTED,
                details={"test": "data"}
            )
        
        # Test invalid details type
        with pytest.raises(ValueError, match="Details must be a dictionary"):
            AuditLogEntry(
                component="test-component",
                action=AuditAction.EMAIL_DETECTED,
                details="invalid_details"
            )
    
    def test_database_config_validation_errors(self):
        """Test database configuration validation error scenarios."""
        # Test invalid pool size
        with pytest.raises(ValueError, match="Pool size must be positive"):
            DatabaseConnectionConfig(
                primary_host="localhost",
                database="test_db",
                username="test_user",
                password="test_pass",
                pool_size=0
            )
        
        # Test negative max overflow
        with pytest.raises(ValueError, match="Max overflow cannot be negative"):
            DatabaseConnectionConfig(
                primary_host="localhost",
                database="test_db",
                username="test_user",
                password="test_pass",
                max_overflow=-1
            )


class TestEnumValues:
    """Test enum value consistency."""
    
    def test_processing_status_values(self):
        """Test ProcessingStatus enum values."""
        assert ProcessingStatus.DETECTED.value == "detected"
        assert ProcessingStatus.PROCESSING.value == "processing"
        assert ProcessingStatus.CLASSIFIED.value == "classified"
        assert ProcessingStatus.PUBLISHED.value == "published"
        assert ProcessingStatus.COMPLETED.value == "completed"
        assert ProcessingStatus.FAILED.value == "failed"
        assert ProcessingStatus.QUARANTINED.value == "quarantined"
    
    def test_audit_action_values(self):
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
    
    def test_connection_health_values(self):
        """Test ConnectionHealth enum values."""
        assert ConnectionHealth.HEALTHY.value == "healthy"
        assert ConnectionHealth.DEGRADED.value == "degraded"
        assert ConnectionHealth.FAILED.value == "failed"
        assert ConnectionHealth.RECOVERING.value == "recovering"