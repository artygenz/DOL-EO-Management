"""
Integration tests for the enhanced database manager.

Tests cover:
- Connection pooling and health monitoring
- Email processing state tracking
- Audit logging with cryptographic integrity
- Automatic failover scenarios
- Performance and error handling
"""

import pytest
import time
import threading
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from contextlib import contextmanager

from src.database.manager import DatabaseManager
from src.database.models import (
    DatabaseConnectionConfig, EmailProcessingState, ProcessingStatus,
    EmailMetadata, AuditLogEntry, AuditAction, ConnectionHealth, FailoverStatus
)
from src.database.exceptions import (
    DatabaseError, ConnectionError, StateTrackingError, 
    AuditError, FailoverError
)


class TestDatabaseManager:
    """Test suite for DatabaseManager class."""
    
    @pytest.fixture
    def db_config(self):
        """Create test database configuration."""
        return DatabaseConnectionConfig(
            primary_host="localhost",
            primary_port=5432,
            backup_host="backup-host",
            backup_port=5432,
            database="test_email_agent",
            username="test_user",
            password="test_password",
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            connection_timeout=10
        )
    
    @pytest.fixture
    def mock_psycopg2_pool(self):
        """Mock psycopg2 connection pool."""
        with patch('src.database.manager.psycopg2.pool') as mock_pool:
            mock_connection = Mock()
            mock_cursor = Mock()
            mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connection.cursor.return_value.__exit__.return_value = None
            
            mock_pool_instance = Mock()
            mock_pool_instance.getconn.return_value = mock_connection
            mock_pool.ThreadedConnectionPool.return_value = mock_pool_instance
            
            yield {
                'pool': mock_pool,
                'pool_instance': mock_pool_instance,
                'connection': mock_connection,
                'cursor': mock_cursor
            }
    
    @pytest.fixture
    def sample_email_metadata(self):
        """Create sample email metadata."""
        return EmailMetadata(
            uid="test-uid-123",
            message_id="<test@example.com>",
            sender="sender@example.com",
            subject="Test Email",
            received_date=datetime.utcnow(),
            account_id="test-account",
            content_hash="abc123def456",
            attachment_count=1,
            size_bytes=1024
        )
    
    @pytest.fixture
    def sample_processing_state(self, sample_email_metadata):
        """Create sample email processing state."""
        return EmailProcessingState(
            email_uid="test-uid-123",
            message_id="<test@example.com>",
            account_id="test-account",
            status=ProcessingStatus.DETECTED,
            metadata=sample_email_metadata,
            classification_result={"type": "NEW_EO", "confidence": 0.95},
            retry_count=0
        )
    
    def test_database_manager_initialization(self, db_config, mock_psycopg2_pool):
        """Test database manager initialization."""
        with patch.object(DatabaseManager, '_initialize_schema'):
            with patch.object(DatabaseManager, '_start_health_monitoring'):
                manager = DatabaseManager(db_config)
                
                assert manager.config == db_config
                assert manager._failover_status == FailoverStatus.PRIMARY_ACTIVE
                assert mock_psycopg2_pool['pool'].ThreadedConnectionPool.call_count == 2  # Primary + backup
    
    def test_primary_pool_creation(self, db_config, mock_psycopg2_pool):
        """Test primary database pool creation."""
        with patch.object(DatabaseManager, '_initialize_schema'):
            with patch.object(DatabaseManager, '_start_health_monitoring'):
                manager = DatabaseManager(db_config)
                
                # Verify primary pool creation
                calls = mock_psycopg2_pool['pool'].ThreadedConnectionPool.call_args_list
                primary_call = calls[0]
                
                assert primary_call[1]['minconn'] == 1
                assert primary_call[1]['maxconn'] == db_config.pool_size + db_config.max_overflow
                assert f"host={db_config.primary_host}" in primary_call[1]['dsn']
    
    def test_backup_pool_creation(self, db_config, mock_psycopg2_pool):
        """Test backup database pool creation."""
        with patch.object(DatabaseManager, '_initialize_schema'):
            with patch.object(DatabaseManager, '_start_health_monitoring'):
                manager = DatabaseManager(db_config)
                
                # Verify backup pool creation
                calls = mock_psycopg2_pool['pool'].ThreadedConnectionPool.call_args_list
                backup_call = calls[1]
                
                assert backup_call[1]['minconn'] == 1
                assert backup_call[1]['maxconn'] == db_config.pool_size + db_config.max_overflow
                assert f"host={db_config.backup_host}" in backup_call[1]['dsn']
    
    def test_get_connection_primary(self, db_config, mock_psycopg2_pool):
        """Test getting connection from primary pool."""
        with patch.object(DatabaseManager, '_initialize_schema'):
            with patch.object(DatabaseManager, '_start_health_monitoring'):
                manager = DatabaseManager(db_config)
                
                with manager.get_connection() as conn:
                    assert conn is not None
                    mock_psycopg2_pool['pool_instance'].getconn.assert_called()
    
    def test_get_connection_backup_forced(self, db_config, mock_psycopg2_pool):
        """Test forcing connection from backup pool."""
        with patch.object(DatabaseManager, '_initialize_schema'):
            with patch.object(DatabaseManager, '_start_health_monitoring'):
                manager = DatabaseManager(db_config)
                
                with manager.get_connection(use_backup=True) as conn:
                    assert conn is not None
                    # Should use backup pool
                    assert mock_psycopg2_pool['pool_instance'].getconn.call_count >= 1
    
    def test_connection_failover(self, db_config, mock_psycopg2_pool):
        """Test automatic failover to backup database."""
        with patch.object(DatabaseManager, '_initialize_schema'):
            with patch.object(DatabaseManager, '_start_health_monitoring'):
                manager = DatabaseManager(db_config)
                
                # Mock primary connection failure
                primary_pool = manager._primary_pool
                backup_pool = manager._backup_pool
                
                # First call fails (primary), second succeeds (backup)
                primary_pool.getconn.side_effect = Exception("Primary connection failed")
                backup_connection = Mock()
                backup_cursor = Mock()
                backup_connection.cursor.return_value.__enter__.return_value = backup_cursor
                backup_connection.cursor.return_value.__exit__.return_value = None
                backup_pool.getconn.return_value = backup_connection
                
                with manager.get_connection() as conn:
                    assert conn == backup_connection
                    assert manager._failover_status == FailoverStatus.BACKUP_ACTIVE
    
    def test_store_email_processing_state_new(self, db_config, mock_psycopg2_pool, sample_processing_state):
        """Test storing new email processing state."""
        with patch.object(DatabaseManager, '_initialize_schema'):
            with patch.object(DatabaseManager, '_start_health_monitoring'):
                manager = DatabaseManager(db_config)
                
                # Mock cursor to return ID
                mock_psycopg2_pool['cursor'].fetchone.return_value = {'id': 123}
                
                state_id = manager.store_email_processing_state(sample_processing_state)
                
                assert state_id == 123
                assert sample_processing_state.id == 123
                mock_psycopg2_pool['cursor'].execute.assert_called()
    
    def test_store_email_processing_state_update(self, db_config, mock_psycopg2_pool, sample_processing_state):
        """Test updating existing email processing state."""
        with patch.object(DatabaseManager, '_initialize_schema'):
            with patch.object(DatabaseManager, '_start_health_monitoring'):
                manager = DatabaseManager(db_config)
                
                # Set existing ID
                sample_processing_state.id = 456
                sample_processing_state.status = ProcessingStatus.COMPLETED
                
                # Mock cursor to return rowcount
                mock_psycopg2_pool['cursor'].rowcount = 1
                
                state_id = manager.store_email_processing_state(sample_processing_state)
                
                assert state_id == 456
                mock_psycopg2_pool['cursor'].execute.assert_called()
    
    def test_get_email_processing_state_found(self, db_config, mock_psycopg2_pool):
        """Test retrieving existing email processing state."""
        with patch.object(DatabaseManager, '_initialize_schema'):
            with patch.object(DatabaseManager, '_start_health_monitoring'):
                manager = DatabaseManager(db_config)
                
                # Mock database response
                mock_row = {
                    'id': 123,
                    'email_uid': 'test-uid-123',
                    'message_id': '<test@example.com>',
                    'account_id': 'test-account',
                    'status': 'detected',
                    'metadata': {
                        'uid': 'test-uid-123',
                        'message_id': '<test@example.com>',
                        'sender': 'sender@example.com',
                        'subject': 'Test Email',
                        'received_date': '2024-01-01T00:00:00',
                        'account_id': 'test-account'
                    },
                    'classification_result': {'type': 'NEW_EO'},
                    'error_message': None,
                    'retry_count': 0,
                    'created_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow(),
                    'processed_at': None
                }
                mock_psycopg2_pool['cursor'].fetchone.return_value = mock_row
                
                state = manager.get_email_processing_state('test-uid-123')
                
                assert state is not None
                assert state.id == 123
                assert state.email_uid == 'test-uid-123'
                assert state.status == ProcessingStatus.DETECTED
    
    def test_get_email_processing_state_not_found(self, db_config, mock_psycopg2_pool):
        """Test retrieving non-existent email processing state."""
        with patch.object(DatabaseManager, '_initialize_schema'):
            with patch.object(DatabaseManager, '_start_health_monitoring'):
                manager = DatabaseManager(db_config)
                
                # Mock no result
                mock_psycopg2_pool['cursor'].fetchone.return_value = None
                
                state = manager.get_email_processing_state('non-existent-uid')
                
                assert state is None
    
    def test_store_audit_entry(self, db_config, mock_psycopg2_pool):
        """Test storing audit log entry."""
        with patch.object(DatabaseManager, '_initialize_schema'):
            with patch.object(DatabaseManager, '_start_health_monitoring'):
                manager = DatabaseManager(db_config)
                
                # Create audit entry
                entry = AuditLogEntry(
                    component="test-component",
                    action=AuditAction.EMAIL_DETECTED,
                    details={"test": "data"},
                    email_uid="test-uid-123",
                    digital_signature="test-signature",
                    hash_chain_current="test-hash"
                )
                
                # Mock cursor to return ID
                mock_psycopg2_pool['cursor'].fetchone.return_value = [789]
                
                entry_id = manager.store_audit_entry(entry)
                
                assert entry_id == 789
                assert entry.id == 789
                mock_psycopg2_pool['cursor'].execute.assert_called()
    
    def test_get_audit_entries_with_filters(self, db_config, mock_psycopg2_pool):
        """Test retrieving audit entries with filters."""
        with patch.object(DatabaseManager, '_initialize_schema'):
            with patch.object(DatabaseManager, '_start_health_monitoring'):
                manager = DatabaseManager(db_config)
                
                # Mock database response
                mock_rows = [{
                    'id': 1,
                    'entry_id': 'test-entry-id',
                    'timestamp': datetime.utcnow(),
                    'component': 'test-component',
                    'action': 'email_detected',
                    'email_uid': 'test-uid-123',
                    'account_id': 'test-account',
                    'user_id': None,
                    'details': {'test': 'data'},
                    'security_classification': 'UNCLASSIFIED',
                    'digital_signature': 'test-signature',
                    'hash_chain_previous': None,
                    'hash_chain_current': 'test-hash'
                }]
                mock_psycopg2_pool['cursor'].fetchall.return_value = mock_rows
                
                entries = manager.get_audit_entries(
                    email_uid='test-uid-123',
                    component='test-component'
                )
                
                assert len(entries) == 1
                assert entries[0].email_uid == 'test-uid-123'
                assert entries[0].component == 'test-component'
    
    def test_check_email_duplicate_new(self, db_config, mock_psycopg2_pool):
        """Test duplicate check for new email."""
        with patch.object(DatabaseManager, '_initialize_schema'):
            with patch.object(DatabaseManager, '_start_health_monitoring'):
                manager = DatabaseManager(db_config)
                
                # Mock no duplicates found
                mock_psycopg2_pool['cursor'].fetchone.return_value = [0]
                
                is_duplicate = manager.check_email_duplicate(
                    'new-uid', '<new@example.com>', 'new-hash', 'test-account'
                )
                
                assert not is_duplicate
                # Should insert new record
                assert mock_psycopg2_pool['cursor'].execute.call_count == 2  # SELECT + INSERT
    
    def test_check_email_duplicate_existing(self, db_config, mock_psycopg2_pool):
        """Test duplicate check for existing email."""
        with patch.object(DatabaseManager, '_initialize_schema'):
            with patch.object(DatabaseManager, '_start_health_monitoring'):
                manager = DatabaseManager(db_config)
                
                # Mock duplicate found
                mock_psycopg2_pool['cursor'].fetchone.return_value = [1]
                
                is_duplicate = manager.check_email_duplicate(
                    'existing-uid', '<existing@example.com>', 'existing-hash', 'test-account'
                )
                
                assert is_duplicate
                # Should only do SELECT, no INSERT
                assert mock_psycopg2_pool['cursor'].execute.call_count == 1
    
    def test_connection_pool_stats(self, db_config, mock_psycopg2_pool):
        """Test getting connection pool statistics."""
        with patch.object(DatabaseManager, '_initialize_schema'):
            with patch.object(DatabaseManager, '_start_health_monitoring'):
                manager = DatabaseManager(db_config)
                
                stats = manager.get_connection_pool_stats()
                
                assert stats.pool_size == db_config.pool_size
                assert stats.total_connections == db_config.pool_size + db_config.max_overflow
                assert stats.health_status == ConnectionHealth.HEALTHY
    
    def test_query_metrics_recording(self, db_config, mock_psycopg2_pool):
        """Test query metrics recording."""
        with patch.object(DatabaseManager, '_initialize_schema'):
            with patch.object(DatabaseManager, '_start_health_monitoring'):
                manager = DatabaseManager(db_config)
                
                # Record a metric
                manager._record_query_metrics("test_query", 150.5, 5, True)
                
                # Check metric was recorded
                assert len(manager._query_metrics) == 1
                metric = manager._query_metrics[0]
                assert metric.query_type == "test_query"
                assert metric.execution_time_ms == 150.5
                assert metric.rows_affected == 5
                assert metric.success is True
    
    def test_health_monitoring_primary_healthy(self, db_config, mock_psycopg2_pool):
        """Test health monitoring with healthy primary database."""
        with patch.object(DatabaseManager, '_initialize_schema'):
            with patch.object(DatabaseManager, '_start_health_monitoring'):
                manager = DatabaseManager(db_config)
                
                # Mock successful health check
                mock_psycopg2_pool['cursor'].execute.return_value = None
                
                manager._check_connection_health()
                
                assert manager._failover_status == FailoverStatus.PRIMARY_ACTIVE
    
    def test_health_monitoring_primary_failed(self, db_config, mock_psycopg2_pool):
        """Test health monitoring with failed primary database."""
        with patch.object(DatabaseManager, '_initialize_schema'):
            with patch.object(DatabaseManager, '_start_health_monitoring'):
                manager = DatabaseManager(db_config)
                
                # Mock primary failure, backup success
                primary_pool = manager._primary_pool
                backup_pool = manager._backup_pool
                
                primary_pool.getconn.side_effect = Exception("Primary failed")
                backup_connection = Mock()
                backup_cursor = Mock()
                backup_connection.cursor.return_value.__enter__.return_value = backup_cursor
                backup_connection.cursor.return_value.__exit__.return_value = None
                backup_pool.getconn.return_value = backup_connection
                
                manager._check_connection_health()
                
                assert manager._failover_status == FailoverStatus.BACKUP_ACTIVE
    
    def test_database_manager_context_manager(self, db_config, mock_psycopg2_pool):
        """Test database manager as context manager."""
        with patch.object(DatabaseManager, '_initialize_schema'):
            with patch.object(DatabaseManager, '_start_health_monitoring'):
                with DatabaseManager(db_config) as manager:
                    assert manager is not None
                
                # Should call close on exit
                mock_psycopg2_pool['pool_instance'].closeall.assert_called()
    
    def test_error_handling_connection_failure(self, db_config, mock_psycopg2_pool):
        """Test error handling for connection failures."""
        with patch.object(DatabaseManager, '_initialize_schema'):
            with patch.object(DatabaseManager, '_start_health_monitoring'):
                manager = DatabaseManager(db_config)
                
                # Mock connection failure
                manager._primary_pool.getconn.side_effect = Exception("Connection failed")
                manager._backup_pool = None  # No backup available
                
                with pytest.raises(ConnectionError):
                    with manager.get_connection():
                        pass
    
    def test_error_handling_state_tracking_failure(self, db_config, mock_psycopg2_pool, sample_processing_state):
        """Test error handling for state tracking failures."""
        with patch.object(DatabaseManager, '_initialize_schema'):
            with patch.object(DatabaseManager, '_start_health_monitoring'):
                manager = DatabaseManager(db_config)
                
                # Mock database error
                mock_psycopg2_pool['cursor'].execute.side_effect = Exception("Database error")
                
                with pytest.raises(StateTrackingError):
                    manager.store_email_processing_state(sample_processing_state)
    
    def test_error_handling_audit_failure(self, db_config, mock_psycopg2_pool):
        """Test error handling for audit logging failures."""
        with patch.object(DatabaseManager, '_initialize_schema'):
            with patch.object(DatabaseManager, '_start_health_monitoring'):
                manager = DatabaseManager(db_config)
                
                # Create audit entry
                entry = AuditLogEntry(
                    component="test-component",
                    action=AuditAction.EMAIL_DETECTED,
                    details={"test": "data"},
                    digital_signature="test-signature",
                    hash_chain_current="test-hash"
                )
                
                # Mock database error
                mock_psycopg2_pool['cursor'].execute.side_effect = Exception("Database error")
                
                with pytest.raises(AuditError):
                    manager.store_audit_entry(entry)
    
    def test_concurrent_operations(self, db_config, mock_psycopg2_pool):
        """Test concurrent database operations."""
        with patch.object(DatabaseManager, '_initialize_schema'):
            with patch.object(DatabaseManager, '_start_health_monitoring'):
                manager = DatabaseManager(db_config)
                
                # Mock successful operations
                mock_psycopg2_pool['cursor'].fetchone.return_value = {'id': 123}
                mock_psycopg2_pool['cursor'].rowcount = 1
                
                results = []
                errors = []
                
                def worker(worker_id):
                    try:
                        state = EmailProcessingState(
                            email_uid=f"test-uid-{worker_id}",
                            message_id=f"<test{worker_id}@example.com>",
                            account_id="test-account",
                            status=ProcessingStatus.DETECTED
                        )
                        result = manager.store_email_processing_state(state)
                        results.append(result)
                    except Exception as e:
                        errors.append(e)
                
                # Run multiple concurrent operations
                threads = []
                for i in range(10):
                    thread = threading.Thread(target=worker, args=(i,))
                    threads.append(thread)
                    thread.start()
                
                # Wait for all threads to complete
                for thread in threads:
                    thread.join()
                
                # Check results
                assert len(errors) == 0
                assert len(results) == 10
    
    def test_schema_initialization(self, db_config, mock_psycopg2_pool):
        """Test database schema initialization."""
        with patch.object(DatabaseManager, '_start_health_monitoring'):
            manager = DatabaseManager(db_config)
            
            # Verify schema creation SQL was executed
            execute_calls = mock_psycopg2_pool['cursor'].execute.call_args_list
            
            # Should have calls for creating tables, indexes, and schema version
            assert len(execute_calls) >= 3
            
            # Check that CREATE TABLE statements were executed
            table_creation_found = any(
                'CREATE TABLE' in str(call) for call in execute_calls
            )
            assert table_creation_found
    
    def test_performance_under_load(self, db_config, mock_psycopg2_pool):
        """Test database performance under load."""
        with patch.object(DatabaseManager, '_initialize_schema'):
            with patch.object(DatabaseManager, '_start_health_monitoring'):
                manager = DatabaseManager(db_config)
                
                # Mock fast responses
                mock_psycopg2_pool['cursor'].fetchone.return_value = {'id': 123}
                
                start_time = time.time()
                
                # Perform many operations
                for i in range(100):
                    state = EmailProcessingState(
                        email_uid=f"test-uid-{i}",
                        message_id=f"<test{i}@example.com>",
                        account_id="test-account",
                        status=ProcessingStatus.DETECTED
                    )
                    manager.store_email_processing_state(state)
                
                end_time = time.time()
                total_time = end_time - start_time
                
                # Should complete reasonably quickly (less than 1 second for mocked operations)
                assert total_time < 1.0
                
                # Check metrics were recorded
                assert len(manager._query_metrics) == 100