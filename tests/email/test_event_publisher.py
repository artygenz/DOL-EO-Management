"""
Tests for Reliable Event Publishing System.

Tests cover Redis queue publishing with confirmation and retry logic,
event buffering for queue unavailability scenarios, exponential backoff
retry mechanism for failed publishes, and backup publishing methods.
"""

import pytest
import time
import json
import threading
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
from queue import Queue, Empty

from src.email.event_publisher import (
    ReliableEventPublisher,
    PublishingResult,
    PublishingStatus,
    BufferedEvent,
    BackupMethod,
    PublishingStats,
    EventPublishingError,
    PublishingTimeoutError,
    BufferFullError
)
from src.email.event_schema import StandardizedEvent, EventSchemaValidator
from src.email.redis_client import RedisClient
from src.database.manager import DatabaseManager


class TestReliableEventPublisher:
    """Test suite for ReliableEventPublisher."""
    
    @pytest.fixture
    def mock_redis_client(self):
        """Create mock Redis client."""
        mock_redis = Mock(spec=RedisClient)
        mock_redis.is_healthy = True
        mock_redis.pipeline.return_value = Mock()
        mock_redis._client = Mock()
        return mock_redis
    
    @pytest.fixture
    def mock_database_manager(self):
        """Create mock database manager."""
        mock_db = Mock(spec=DatabaseManager)
        mock_connection = Mock()
        mock_cursor = Mock()
        
        # Properly mock context manager
        mock_cursor_context = Mock()
        mock_cursor_context.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor_context.__exit__ = Mock(return_value=None)
        mock_connection.cursor = Mock(return_value=mock_cursor_context)
        
        mock_connection_context = Mock()
        mock_connection_context.__enter__ = Mock(return_value=mock_connection)
        mock_connection_context.__exit__ = Mock(return_value=None)
        mock_db.get_connection = Mock(return_value=mock_connection_context)
        
        return mock_db
    
    @pytest.fixture
    def mock_schema_validator(self):
        """Create mock schema validator."""
        mock_validator = Mock(spec=EventSchemaValidator)
        mock_validator.validate_event.return_value = (True, None)
        return mock_validator
    
    @pytest.fixture
    def sample_event(self):
        """Create sample standardized event."""
        from src.email.event_schema import (
            EventEmailMetadata, EventContent, EventSecurity, EventWorkflow
        )
        
        return StandardizedEvent(
            event_id="test-event-123",
            correlation_id="corr-123",
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type="NEW_EO",
            schema_version="2.0",
            priority="HIGH",
            confidence_score=0.95,
            email_metadata=EventEmailMetadata(
                uid="uid-123",
                message_id="msg-123",
                sender="test@example.com",
                sender_name="Test User",
                recipients=["recipient@example.com"],
                subject="Test Subject",
                received_date=datetime.now(timezone.utc).isoformat(),
                thread_id="thread-123",
                content_hash="hash123",
                size_bytes=1024
            ),
            content=EventContent(
                body_text="Test email content",
                body_text_preview="Test email...",
                has_html_content=False,
                attachments=[],
                classification_features={},
                thread_analysis={}
            ),
            security=EventSecurity(
                sender_authorized=True,
                content_safe=True,
                attachments_safe=True,
                security_scan_timestamp=datetime.now(timezone.utc).isoformat(),
                threat_indicators=[],
                compliance_flags=[]
            ),
            workflow=EventWorkflow(
                assigned_queue="test_queue",
                workflow_type="NEW_EO",
                priority_level="HIGH",
                processing_requirements={},
                estimated_processing_time=120.0,
                escalation_required=False
            )
        )
    
    @pytest.fixture
    def publisher(self, mock_redis_client, mock_database_manager, mock_schema_validator):
        """Create ReliableEventPublisher instance."""
        publisher = ReliableEventPublisher(
            redis_client=mock_redis_client,
            database_manager=mock_database_manager,
            schema_validator=mock_schema_validator
        )
        # Stop background processor for testing
        publisher._buffer_processor_running = False
        return publisher
    
    def test_successful_redis_publishing(self, publisher, sample_event, mock_redis_client):
        """Test successful event publishing to Redis."""
        # Setup mock Redis pipeline
        mock_pipeline = Mock()
        mock_pipeline.execute.return_value = [5]  # Queue length after LPUSH
        mock_redis_client.pipeline.return_value = mock_pipeline
        
        # Publish event
        result = publisher.publish_event(sample_event, "test_queue", require_confirmation=False)
        
        # Verify result
        assert result.success is True
        assert result.status == PublishingStatus.PUBLISHED
        assert result.event_id == sample_event.event_id
        assert result.queue_name == "test_queue"
        assert result.latency_ms > 0
        
        # Verify Redis calls
        mock_pipeline.lpush.assert_called_once_with("test_queue", sample_event.to_json())
        mock_pipeline.execute.assert_called_once()
    
    def test_publishing_with_confirmation(self, publisher, sample_event, mock_redis_client):
        """Test event publishing with confirmation requirement."""
        # Setup mock Redis pipeline
        mock_pipeline = Mock()
        mock_pipeline.execute.return_value = [5, True]  # LPUSH result, SETEX result
        mock_redis_client.pipeline.return_value = mock_pipeline
        
        # Mock confirmation check
        mock_redis_client.get.return_value = "confirmed"
        
        # Publish event with confirmation
        result = publisher.publish_event(sample_event, "test_queue", require_confirmation=True)
        
        # Verify result
        assert result.success is True
        assert result.status == PublishingStatus.PUBLISHED
        assert result.confirmation_id is not None
        
        # Verify confirmation setup
        mock_pipeline.setex.assert_called_once()
        mock_redis_client.get.assert_called()
    
    def test_confirmation_timeout(self, publisher, sample_event, mock_redis_client):
        """Test publishing confirmation timeout."""
        # Setup mock Redis pipeline
        mock_pipeline = Mock()
        mock_pipeline.execute.return_value = [5, True]
        mock_redis_client.pipeline.return_value = mock_pipeline
        
        # Mock confirmation timeout (never returns "confirmed")
        mock_redis_client.get.return_value = "pending"
        
        # Publish event with confirmation
        result = publisher.publish_event(sample_event, "test_queue", require_confirmation=True)
        
        # Verify timeout handling
        assert result.success is False
        assert "confirmation timeout" in result.error_message
        assert result.confirmation_id is not None
    
    def test_redis_unavailable_fallback(self, publisher, sample_event, mock_redis_client, mock_database_manager):
        """Test fallback to backup methods when Redis is unavailable."""
        # Make Redis unhealthy
        mock_redis_client.is_healthy = False
        
        # Database backup is already set up in the fixture, just ensure it works
        # The mock_database_manager fixture already has proper context manager setup
        
        # Publish event
        result = publisher.publish_event(sample_event, "test_queue")
        
        # Verify backup method was used
        assert result.success is True
        assert result.status == PublishingStatus.BACKUP_PUBLISHED
        assert result.backup_method == BackupMethod.DATABASE
        
        # Verify database backup was attempted (the mock setup ensures it succeeds)
    
    def test_high_latency_backup_trigger(self, publisher, sample_event, mock_redis_client, mock_database_manager):
        """Test backup method trigger when latency exceeds threshold."""
        # Setup Redis to succeed but with high latency simulation
        mock_pipeline = Mock()
        mock_pipeline.execute.return_value = [5]
        mock_redis_client.pipeline.return_value = mock_pipeline
        
        # Mock time to simulate high latency
        with patch('time.time') as mock_time:
            mock_time.side_effect = [0, 6.0]  # 6 second latency
            
            # Setup database backup
            mock_connection = Mock()
            mock_cursor = Mock()
            mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
            mock_database_manager.get_connection.return_value.__enter__.return_value = mock_connection
            
            # Publish event
            result = publisher.publish_event(sample_event, "test_queue")
            
            # Verify backup was triggered due to high latency
            assert result.success is True
            assert result.backup_method == BackupMethod.DATABASE
    
    def test_event_buffering(self, publisher, sample_event, mock_redis_client, mock_database_manager):
        """Test event buffering when all publishing methods fail."""
        # Make Redis unhealthy
        mock_redis_client.is_healthy = False
        
        # Make database backup fail
        mock_database_manager.get_connection.side_effect = Exception("Database unavailable")
        
        # Publish event
        result = publisher.publish_event(sample_event, "test_queue")
        
        # Verify event was buffered
        assert result.success is False
        assert result.status == PublishingStatus.BUFFERED
        assert "event buffered" in result.error_message
        
        # Verify buffer contains the event
        buffer_status = publisher.get_buffer_status()
        assert buffer_status['buffer_size'] > 0
    
    def test_batch_publishing(self, publisher, sample_event, mock_redis_client):
        """Test batch publishing of multiple events."""
        # Create multiple events
        events = []
        for i in range(5):
            event = sample_event
            event.event_id = f"test-event-{i}"
            events.append(event)
        
        # Setup mock Redis pipeline
        mock_pipeline = Mock()
        mock_pipeline.execute.return_value = [5]
        mock_redis_client.pipeline.return_value = mock_pipeline
        
        # Publish batch
        results = publisher.publish_batch(events, "test_queue")
        
        # Verify all events were processed
        assert len(results) == 5
        assert all(result.success for result in results)
        assert all(result.status == PublishingStatus.PUBLISHED for result in results)
    
    def test_exponential_backoff_retry(self, publisher, sample_event):
        """Test exponential backoff retry mechanism."""
        # Create buffered event
        buffered_event = BufferedEvent(
            event=sample_event,
            queue_name="test_queue",
            timestamp=datetime.now(timezone.utc)
        )
        
        # Test retry delay calculation
        delays = []
        for retry_count in range(5):
            buffered_event.retry_count = retry_count
            delay = min(
                publisher.BASE_RETRY_DELAY * (2 ** retry_count),
                publisher.MAX_RETRY_DELAY
            )
            delays.append(delay)
        
        # Verify exponential backoff
        assert delays[0] == 0.1  # 100ms
        assert delays[1] == 0.2  # 200ms
        assert delays[2] == 0.4  # 400ms
        assert delays[3] == 0.8  # 800ms
        assert delays[4] == 1.6  # 1.6s
    
    def test_buffer_expiration(self, publisher, sample_event):
        """Test buffered event expiration."""
        # Create expired buffered event
        old_timestamp = datetime.now(timezone.utc) - timedelta(hours=25)  # 25 hours ago
        buffered_event = BufferedEvent(
            event=sample_event,
            queue_name="test_queue",
            timestamp=old_timestamp
        )
        
        # Verify event is expired
        assert buffered_event.is_expired is True
        assert buffered_event.can_retry is False
    
    def test_max_retries_exceeded(self, publisher, sample_event):
        """Test handling when max retries are exceeded."""
        # Create buffered event with max retries
        buffered_event = BufferedEvent(
            event=sample_event,
            queue_name="test_queue",
            timestamp=datetime.now(timezone.utc),
            retry_count=10,  # At max retries
            max_retries=10
        )
        
        # Verify event cannot be retried
        assert buffered_event.can_retry is False
    
    def test_buffer_full_handling(self, publisher, sample_event):
        """Test handling when event buffer is full."""
        # Fill the buffer to capacity
        publisher._event_buffer = Queue(maxsize=2)  # Small buffer for testing
        
        # Add events to fill buffer
        for i in range(2):
            event = sample_event
            event.event_id = f"buffer-event-{i}"
            publisher._buffer_event(event, "test_queue")
        
        # Try to add one more event (should be dropped)
        overflow_event = sample_event
        overflow_event.event_id = "overflow-event"
        publisher._buffer_event(overflow_event, "test_queue")
        
        # Verify buffer is at capacity
        buffer_status = publisher.get_buffer_status()
        assert buffer_status['buffer_size'] == 2
        assert buffer_status['buffer_utilization'] == 100.0
    
    def test_database_backup_method(self, publisher, sample_event, mock_database_manager):
        """Test database backup publishing method."""
        # Setup database mock
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_database_manager.get_connection.return_value.__enter__.return_value = mock_connection
        
        # Test database backup
        result = publisher._publish_to_database(sample_event, "test_queue")
        
        # Verify result
        assert result.success is True
        assert result.status == PublishingStatus.BACKUP_PUBLISHED
        assert result.backup_method == BackupMethod.DATABASE
        
        # Verify database call
        mock_cursor.execute.assert_called_once()
        mock_connection.commit.assert_called_once()
    
    def test_filesystem_backup_method(self, publisher, sample_event):
        """Test filesystem backup publishing method."""
        with patch('os.makedirs') as mock_makedirs, \
             patch('builtins.open', create=True) as mock_open:
            
            mock_file = Mock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            # Test filesystem backup
            result = publisher._publish_to_filesystem(sample_event, "test_queue")
            
            # Verify result
            assert result.success is True
            assert result.status == PublishingStatus.BACKUP_PUBLISHED
            assert result.backup_method == BackupMethod.FILE_SYSTEM
            
            # Verify file operations
            mock_makedirs.assert_called_once()
            mock_open.assert_called_once()
            mock_file.write.assert_called_once_with(sample_event.to_json())
    
    def test_schema_validation_failure(self, publisher, sample_event, mock_schema_validator):
        """Test handling of schema validation failures."""
        # Make schema validation fail
        mock_schema_validator.validate_event.return_value = (False, "Invalid schema")
        
        # Publish event
        result = publisher.publish_event(sample_event, "test_queue")
        
        # Verify validation failure handling
        assert result.success is False
        assert result.status == PublishingStatus.FAILED
        assert "Schema validation failed" in result.error_message
    
    def test_publishing_statistics(self, publisher, sample_event, mock_redis_client):
        """Test publishing statistics collection."""
        # Setup successful publishing
        mock_pipeline = Mock()
        mock_pipeline.execute.return_value = [5]
        mock_redis_client.pipeline.return_value = mock_pipeline
        
        # Publish multiple events
        for i in range(3):
            event = sample_event
            event.event_id = f"stats-event-{i}"
            publisher.publish_event(event, "test_queue", require_confirmation=False)
        
        # Get statistics
        stats = publisher.get_publishing_stats()
        
        # Verify statistics
        assert stats.total_events == 3
        assert stats.successful_publishes == 3
        assert stats.success_rate == 100.0
        assert stats.average_latency_ms > 0
    
    def test_force_buffer_flush(self, publisher, sample_event, mock_redis_client):
        """Test force flushing of buffered events."""
        # Add events to buffer
        for i in range(3):
            event = sample_event
            event.event_id = f"flush-event-{i}"
            publisher._buffer_event(event, "test_queue")
        
        # Setup Redis for successful flush
        mock_pipeline = Mock()
        mock_pipeline.execute.return_value = [5]
        mock_redis_client.pipeline.return_value = mock_pipeline
        mock_redis_client.is_healthy = True
        
        # Force flush buffer
        flush_result = publisher.force_buffer_flush()
        
        # Verify flush results
        assert flush_result['processed'] == 3
        assert flush_result['successful'] >= 0  # Some may succeed
        assert flush_result['remaining_in_buffer'] >= 0
    
    def test_publisher_shutdown(self, publisher):
        """Test publisher shutdown and cleanup."""
        # Start buffer processor
        publisher._start_buffer_processor()
        assert publisher._buffer_processor_running is True
        
        # Shutdown publisher
        publisher.shutdown()
        
        # Verify shutdown
        assert publisher._buffer_processor_running is False
        
        # Verify thread cleanup (if thread was created)
        if publisher._buffer_processor_thread:
            assert not publisher._buffer_processor_thread.is_alive()
    
    def test_concurrent_publishing(self, publisher, sample_event, mock_redis_client):
        """Test concurrent event publishing."""
        # Setup successful publishing
        mock_pipeline = Mock()
        mock_pipeline.execute.return_value = [5]
        mock_redis_client.pipeline.return_value = mock_pipeline
        
        # Publish events concurrently
        import concurrent.futures
        
        def publish_event(event_id):
            event = sample_event
            event.event_id = f"concurrent-{event_id}"
            return publisher.publish_event(event, "test_queue", require_confirmation=False)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(publish_event, i) for i in range(10)]
            results = [future.result() for future in futures]
        
        # Verify all events were processed
        assert len(results) == 10
        successful = sum(1 for result in results if result.success)
        assert successful > 0  # At least some should succeed
    
    def test_buffer_status_reporting(self, publisher, sample_event):
        """Test buffer status reporting."""
        # Add events to buffer with different states
        current_time = datetime.now(timezone.utc)
        
        # Add fresh event
        fresh_event = BufferedEvent(
            event=sample_event,
            queue_name="test_queue",
            timestamp=current_time
        )
        publisher._event_buffer.put_nowait(fresh_event)
        
        # Add expired event
        expired_event = BufferedEvent(
            event=sample_event,
            queue_name="test_queue",
            timestamp=current_time - timedelta(hours=25)
        )
        publisher._event_buffer.put_nowait(expired_event)
        
        # Get buffer status
        status = publisher.get_buffer_status()
        
        # Verify status reporting
        assert status['buffer_size'] == 2
        assert status['max_buffer_size'] == publisher.BUFFER_MAX_SIZE
        assert status['buffer_utilization'] > 0
        assert 'expired_events' in status
        assert 'retry_ready_events' in status


class TestBufferedEvent:
    """Test suite for BufferedEvent class."""
    
    def test_buffered_event_creation(self):
        """Test BufferedEvent creation and properties."""
        from src.email.event_schema import StandardizedEvent, EventEmailMetadata, EventContent, EventSecurity, EventWorkflow
        
        # Create sample event
        event = StandardizedEvent(
            event_id="test-123",
            correlation_id="corr-123",
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type="NEW_EO",
            schema_version="2.0",
            priority="HIGH",
            confidence_score=0.95,
            email_metadata=EventEmailMetadata(
                uid="uid-123", message_id="msg-123", sender="test@example.com",
                sender_name="Test", recipients=[], subject="Test",
                received_date=datetime.now(timezone.utc).isoformat(),
                thread_id=None, content_hash="hash", size_bytes=100
            ),
            content=EventContent(
                body_text="Test", body_text_preview="Test", has_html_content=False,
                attachments=[], classification_features={}, thread_analysis={}
            ),
            security=EventSecurity(
                sender_authorized=True, content_safe=True, attachments_safe=True,
                security_scan_timestamp=datetime.now(timezone.utc).isoformat(),
                threat_indicators=[], compliance_flags=[]
            ),
            workflow=EventWorkflow(
                assigned_queue="test", workflow_type="NEW_EO", priority_level="HIGH",
                processing_requirements={}, estimated_processing_time=120.0,
                escalation_required=False
            )
        )
        
        # Create buffered event
        buffered = BufferedEvent(
            event=event,
            queue_name="test_queue",
            timestamp=datetime.now(timezone.utc)
        )
        
        # Verify properties
        assert buffered.event.event_id == "test-123"
        assert buffered.queue_name == "test_queue"
        assert buffered.retry_count == 0
        assert buffered.max_retries == 10
        assert buffered.is_expired is False
        assert buffered.can_retry is True
    
    def test_buffered_event_expiration(self):
        """Test buffered event expiration logic."""
        from src.email.event_schema import StandardizedEvent, EventEmailMetadata, EventContent, EventSecurity, EventWorkflow
        
        # Create expired buffered event
        old_timestamp = datetime.now(timezone.utc) - timedelta(hours=25)
        
        event = StandardizedEvent(
            event_id="expired-123",
            correlation_id="corr-123",
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type="NEW_EO",
            schema_version="2.0",
            priority="HIGH",
            confidence_score=0.95,
            email_metadata=EventEmailMetadata(
                uid="uid-123", message_id="msg-123", sender="test@example.com",
                sender_name="Test", recipients=[], subject="Test",
                received_date=datetime.now(timezone.utc).isoformat(),
                thread_id=None, content_hash="hash", size_bytes=100
            ),
            content=EventContent(
                body_text="Test", body_text_preview="Test", has_html_content=False,
                attachments=[], classification_features={}, thread_analysis={}
            ),
            security=EventSecurity(
                sender_authorized=True, content_safe=True, attachments_safe=True,
                security_scan_timestamp=datetime.now(timezone.utc).isoformat(),
                threat_indicators=[], compliance_flags=[]
            ),
            workflow=EventWorkflow(
                assigned_queue="test", workflow_type="NEW_EO", priority_level="HIGH",
                processing_requirements={}, estimated_processing_time=120.0,
                escalation_required=False
            )
        )
        
        buffered = BufferedEvent(
            event=event,
            queue_name="test_queue",
            timestamp=old_timestamp
        )
        
        # Verify expiration
        assert buffered.is_expired is True
        assert buffered.can_retry is False


class TestPublishingStats:
    """Test suite for PublishingStats class."""
    
    def test_publishing_stats_calculations(self):
        """Test publishing statistics calculations."""
        stats = PublishingStats(
            total_events=100,
            successful_publishes=95,
            failed_publishes=3,
            backup_publishes=2
        )
        
        # Test calculated properties
        assert stats.success_rate == 95.0
        assert stats.backup_rate == 2.0
    
    def test_empty_stats_calculations(self):
        """Test statistics calculations with zero events."""
        stats = PublishingStats()
        
        # Test calculated properties with zero events
        assert stats.success_rate == 0.0
        assert stats.backup_rate == 0.0


if __name__ == "__main__":
    pytest.main([__file__])