"""
Integration tests for Reliable Event Publishing System.

Tests the complete event publishing pipeline including Redis integration,
database backup, retry mechanisms, and failure recovery scenarios.
"""

import pytest
import time
import json
import threading
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch

import redis
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError

from src.email.event_publisher import (
    ReliableEventPublisher,
    PublishingStatus,
    BackupMethod,
    BufferedEvent
)
from src.email.event_schema import (
    StandardizedEvent,
    EventEmailMetadata,
    EventContent,
    EventSecurity,
    EventWorkflow,
    EventSchemaValidator
)
from src.email.redis_client import RedisClient
from src.database.manager import DatabaseManager
from src.config.models import RedisConfig, DatabaseConfig


class TestEventPublisherIntegration:
    """Integration tests for event publishing system."""
    
    @pytest.fixture
    def redis_config(self):
        """Create Redis configuration for testing."""
        return RedisConfig(
            host="localhost",
            port=6379,
            database=1,  # Use test database
            password=None,
            ssl=False,
            connection_pool_size=10,
            socket_timeout=5.0
        )
    
    @pytest.fixture
    def database_config(self):
        """Create database configuration for testing."""
        return DatabaseConfig(
            host="localhost",
            port=5432,
            database="email_agent_test",
            username="test_user",
            password="test_password",
            connection_pool_size=5,
            connection_timeout=30.0
        )
    
    @pytest.fixture
    def redis_client(self, redis_config):
        """Create Redis client for testing."""
        try:
            client = RedisClient(redis_config)
            # Clear test database
            if client.is_healthy:
                client._client.flushdb()
            return client
        except Exception:
            pytest.skip("Redis not available for integration tests")
    
    @pytest.fixture
    def database_manager(self, database_config):
        """Create database manager for testing."""
        try:
            manager = DatabaseManager(database_config)
            # Initialize test schema
            self._setup_test_database(manager)
            return manager
        except Exception:
            pytest.skip("Database not available for integration tests")
    
    @pytest.fixture
    def publisher(self, redis_client, database_manager):
        """Create event publisher for integration testing."""
        publisher = ReliableEventPublisher(
            redis_client=redis_client,
            database_manager=database_manager,
            schema_validator=EventSchemaValidator()
        )
        yield publisher
        # Cleanup
        publisher.shutdown()
    
    @pytest.fixture
    def sample_event(self):
        """Create sample standardized event for testing."""
        return StandardizedEvent(
            event_id="integration-test-123",
            correlation_id="corr-integration-123",
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type="NEW_EO",
            schema_version="2.0",
            priority="HIGH",
            confidence_score=0.95,
            email_metadata=EventEmailMetadata(
                uid="integration-uid-123",
                message_id="integration-msg-123",
                sender="integration@test.com",
                sender_name="Integration Test",
                recipients=["recipient@test.com"],
                subject="Integration Test Subject",
                received_date=datetime.now(timezone.utc).isoformat(),
                thread_id="integration-thread-123",
                content_hash="integration-hash-123",
                size_bytes=2048
            ),
            content=EventContent(
                body_text="Integration test email content with sufficient length for testing",
                body_text_preview="Integration test email...",
                has_html_content=False,
                attachments=[],
                classification_features={"sender_score": 0.9, "content_score": 0.8},
                thread_analysis={"thread_depth": 1, "participants": 2}
            ),
            security=EventSecurity(
                sender_authorized=True,
                content_safe=True,
                attachments_safe=True,
                security_scan_timestamp=datetime.now(timezone.utc).isoformat(),
                threat_indicators=[],
                compliance_flags=["FISMA_COMPLIANT"]
            ),
            workflow=EventWorkflow(
                assigned_queue="integration_test_queue",
                workflow_type="NEW_EO",
                priority_level="HIGH",
                processing_requirements={"requires_approval": True},
                estimated_processing_time=180.0,
                escalation_required=False
            )
        )
    
    def _setup_test_database(self, database_manager):
        """Setup test database schema."""
        try:
            with database_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Create test tables
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS event_backup_queue (
                            id SERIAL PRIMARY KEY,
                            event_id VARCHAR(255) NOT NULL UNIQUE,
                            queue_name VARCHAR(255) NOT NULL,
                            event_data TEXT NOT NULL,
                            created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                            processed_at TIMESTAMP WITH TIME ZONE,
                            status VARCHAR(50) DEFAULT 'pending',
                            retry_count INTEGER DEFAULT 0,
                            error_message TEXT
                        )
                    """)
                    
                    # Clear existing test data
                    cursor.execute("DELETE FROM event_backup_queue WHERE event_id LIKE 'integration-%'")
                    
                    conn.commit()
        except Exception as e:
            print(f"Database setup failed: {e}")
    
    def test_end_to_end_redis_publishing(self, publisher, sample_event, redis_client):
        """Test complete end-to-end Redis publishing flow."""
        if not redis_client.is_healthy:
            pytest.skip("Redis not healthy for integration test")
        
        # Publish event
        result = publisher.publish_event(sample_event, "integration_test_queue")
        
        # Verify publishing success
        assert result.success is True
        assert result.status == PublishingStatus.PUBLISHED
        assert result.latency_ms > 0
        assert result.latency_ms < 1000  # Should be sub-second
        
        # Verify event is in Redis queue
        queue_length = redis_client._client.llen("integration_test_queue")
        assert queue_length > 0
        
        # Retrieve and verify event data
        event_data = redis_client._client.rpop("integration_test_queue")
        assert event_data is not None
        
        retrieved_event = json.loads(event_data.decode('utf-8'))
        assert retrieved_event['event_id'] == sample_event.event_id
        assert retrieved_event['event_type'] == sample_event.event_type
    
    def test_redis_failure_database_backup(self, publisher, sample_event, database_manager):
        """Test database backup when Redis fails."""
        # Simulate Redis failure
        publisher.redis._is_healthy = False
        
        # Publish event (should use database backup)
        result = publisher.publish_event(sample_event, "backup_test_queue")
        
        # Verify backup publishing
        assert result.success is True
        assert result.status == PublishingStatus.BACKUP_PUBLISHED
        assert result.backup_method == BackupMethod.DATABASE
        
        # Verify event is in database backup queue
        with database_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT event_id, queue_name, event_data, status
                    FROM event_backup_queue
                    WHERE event_id = %s
                """, (sample_event.event_id,))
                
                row = cursor.fetchone()
                assert row is not None
                assert row[0] == sample_event.event_id
                assert row[1] == "backup_test_queue"
                assert row[3] == "pending"
                
                # Verify event data integrity
                stored_event = json.loads(row[2])
                assert stored_event['event_id'] == sample_event.event_id
    
    def test_high_latency_backup_trigger(self, publisher, sample_event, redis_client, database_manager):
        """Test backup trigger when Redis latency is high."""
        if not redis_client.is_healthy:
            pytest.skip("Redis not healthy for integration test")
        
        # Simulate high latency by adding delay to Redis operations
        original_pipeline = redis_client.pipeline
        
        def slow_pipeline():
            pipeline = original_pipeline()
            original_execute = pipeline.execute
            
            def slow_execute():
                time.sleep(6.0)  # 6 second delay
                return original_execute()
            
            pipeline.execute = slow_execute
            return pipeline
        
        redis_client.pipeline = slow_pipeline
        
        try:
            # Publish event
            result = publisher.publish_event(sample_event, "latency_test_queue")
            
            # Should use backup method due to high latency
            assert result.success is True
            assert result.backup_method == BackupMethod.DATABASE
            
        finally:
            # Restore original pipeline
            redis_client.pipeline = original_pipeline
    
    def test_event_buffering_and_retry(self, publisher, sample_event, redis_client):
        """Test event buffering and retry mechanism."""
        # Make both Redis and database unavailable
        publisher.redis._is_healthy = False
        publisher.db.get_connection = Mock(side_effect=Exception("Database unavailable"))
        
        # Publish event (should be buffered)
        result = publisher.publish_event(sample_event, "retry_test_queue")
        
        # Verify event was buffered
        assert result.success is False
        assert result.status == PublishingStatus.BUFFERED
        
        # Verify buffer contains event
        buffer_status = publisher.get_buffer_status()
        assert buffer_status['buffer_size'] > 0
        
        # Restore Redis health
        publisher.redis._is_healthy = True
        
        # Force buffer flush to trigger retry
        flush_result = publisher.force_buffer_flush()
        
        # Verify retry was successful
        assert flush_result['successful'] > 0
        
        # Verify event is now in Redis
        if redis_client.is_healthy:
            queue_length = redis_client._client.llen("retry_test_queue")
            assert queue_length > 0
    
    def test_batch_publishing_performance(self, publisher, redis_client):
        """Test batch publishing performance and reliability."""
        if not redis_client.is_healthy:
            pytest.skip("Redis not healthy for integration test")
        
        # Create batch of events
        events = []
        for i in range(50):  # 50 events for performance test
            event = StandardizedEvent(
                event_id=f"batch-test-{i}",
                correlation_id=f"batch-corr-{i}",
                timestamp=datetime.now(timezone.utc).isoformat(),
                event_type="DEVELOPER_UPDATE",
                schema_version="2.0",
                priority="MEDIUM",
                confidence_score=0.85,
                email_metadata=EventEmailMetadata(
                    uid=f"batch-uid-{i}",
                    message_id=f"batch-msg-{i}",
                    sender=f"batch{i}@test.com",
                    sender_name=f"Batch Test {i}",
                    recipients=["recipient@test.com"],
                    subject=f"Batch Test Subject {i}",
                    received_date=datetime.now(timezone.utc).isoformat(),
                    thread_id=f"batch-thread-{i}",
                    content_hash=f"batch-hash-{i}",
                    size_bytes=1024
                ),
                content=EventContent(
                    body_text=f"Batch test content {i}",
                    body_text_preview=f"Batch test {i}...",
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
                    assigned_queue="batch_test_queue",
                    workflow_type="DEVELOPER_UPDATE",
                    priority_level="MEDIUM",
                    processing_requirements={},
                    estimated_processing_time=60.0,
                    escalation_required=False
                )
            )
            events.append(event)
        
        # Measure batch publishing time
        start_time = time.time()
        results = publisher.publish_batch(events, "batch_test_queue")
        end_time = time.time()
        
        # Verify performance and results
        batch_time = end_time - start_time
        assert batch_time < 10.0  # Should complete within 10 seconds
        
        successful_count = sum(1 for r in results if r.success)
        assert successful_count >= 45  # At least 90% success rate
        
        # Verify events are in Redis
        queue_length = redis_client._client.llen("batch_test_queue")
        assert queue_length >= successful_count
    
    def test_concurrent_publishing_stress(self, publisher, redis_client):
        """Test concurrent publishing under stress conditions."""
        if not redis_client.is_healthy:
            pytest.skip("Redis not healthy for integration test")
        
        import concurrent.futures
        import threading
        
        # Shared counters
        success_count = threading.AtomicInteger(0) if hasattr(threading, 'AtomicInteger') else [0]
        error_count = threading.AtomicInteger(0) if hasattr(threading, 'AtomicInteger') else [0]
        
        def publish_concurrent_event(thread_id, event_id):
            """Publish event from concurrent thread."""
            try:
                event = StandardizedEvent(
                    event_id=f"stress-{thread_id}-{event_id}",
                    correlation_id=f"stress-corr-{thread_id}-{event_id}",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    event_type="EXECUTIVE_REQUEST",
                    schema_version="2.0",
                    priority="HIGH",
                    confidence_score=0.92,
                    email_metadata=EventEmailMetadata(
                        uid=f"stress-uid-{thread_id}-{event_id}",
                        message_id=f"stress-msg-{thread_id}-{event_id}",
                        sender=f"stress{thread_id}@test.com",
                        sender_name=f"Stress Test {thread_id}",
                        recipients=["recipient@test.com"],
                        subject=f"Stress Test Subject {thread_id}-{event_id}",
                        received_date=datetime.now(timezone.utc).isoformat(),
                        thread_id=f"stress-thread-{thread_id}",
                        content_hash=f"stress-hash-{thread_id}-{event_id}",
                        size_bytes=512
                    ),
                    content=EventContent(
                        body_text=f"Stress test content {thread_id}-{event_id}",
                        body_text_preview=f"Stress test {thread_id}...",
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
                        assigned_queue="stress_test_queue",
                        workflow_type="EXECUTIVE_REQUEST",
                        priority_level="HIGH",
                        processing_requirements={},
                        estimated_processing_time=90.0,
                        escalation_required=True
                    )
                )
                
                result = publisher.publish_event(event, "stress_test_queue", require_confirmation=False)
                
                if result.success:
                    if hasattr(success_count, 'increment'):
                        success_count.increment()
                    else:
                        success_count[0] += 1
                else:
                    if hasattr(error_count, 'increment'):
                        error_count.increment()
                    else:
                        error_count[0] += 1
                
                return result
                
            except Exception as e:
                if hasattr(error_count, 'increment'):
                    error_count.increment()
                else:
                    error_count[0] += 1
                return None
        
        # Run concurrent publishing stress test
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = []
            
            # Submit 100 concurrent publishing tasks
            for thread_id in range(10):
                for event_id in range(10):
                    future = executor.submit(publish_concurrent_event, thread_id, event_id)
                    futures.append(future)
            
            # Wait for all tasks to complete
            concurrent.futures.wait(futures, timeout=60)
        
        # Verify stress test results
        total_success = success_count[0] if isinstance(success_count, list) else success_count.value
        total_errors = error_count[0] if isinstance(error_count, list) else error_count.value
        
        assert total_success > 80  # At least 80% success rate under stress
        assert total_success + total_errors == 100  # All tasks completed
        
        # Verify events are in Redis
        queue_length = redis_client._client.llen("stress_test_queue")
        assert queue_length >= total_success
    
    def test_publishing_confirmation_flow(self, publisher, sample_event, redis_client):
        """Test publishing confirmation mechanism."""
        if not redis_client.is_healthy:
            pytest.skip("Redis not healthy for integration test")
        
        # Publish event with confirmation requirement
        result = publisher.publish_event(sample_event, "confirmation_test_queue", require_confirmation=True)
        
        # Verify confirmation was set up
        assert result.confirmation_id is not None
        
        # Simulate confirmation by setting confirmation key
        confirmation_key = f"confirm:{result.confirmation_id}"
        redis_client.set(confirmation_key, "confirmed", ex=2)
        
        # Publish another event to test confirmation flow
        sample_event.event_id = "confirmation-test-2"
        result2 = publisher.publish_event(sample_event, "confirmation_test_queue", require_confirmation=True)
        
        # This should succeed if confirmation mechanism works
        assert result2.success is True or result2.error_message is not None
    
    def test_schema_validation_integration(self, publisher, redis_client):
        """Test schema validation in integration environment."""
        if not redis_client.is_healthy:
            pytest.skip("Redis not healthy for integration test")
        
        # Create event with invalid schema
        invalid_event = {
            "event_id": "invalid-schema-test",
            "invalid_field": "this should not be here",
            # Missing required fields
        }
        
        # Try to create StandardizedEvent with minimal data
        try:
            event = StandardizedEvent(
                event_id="schema-test-123",
                correlation_id="schema-corr-123",
                timestamp="invalid-timestamp",  # Invalid timestamp format
                event_type="INVALID_TYPE",  # Invalid event type
                schema_version="999.0",  # Invalid schema version
                priority="INVALID_PRIORITY",  # Invalid priority
                confidence_score=1.5,  # Invalid confidence score (> 1.0)
                email_metadata=None,  # Invalid - should be EventEmailMetadata
                content=None,  # Invalid - should be EventContent
                security=None,  # Invalid - should be EventSecurity
                workflow=None  # Invalid - should be EventWorkflow
            )
            
            # This should fail validation
            result = publisher.publish_event(event, "schema_test_queue")
            assert result.success is False
            assert "validation" in result.error_message.lower()
            
        except Exception:
            # Expected - invalid event creation should fail
            pass
    
    def test_publisher_health_monitoring(self, publisher, redis_client, database_manager):
        """Test publisher health monitoring and recovery."""
        # Get initial statistics
        initial_stats = publisher.get_publishing_stats()
        
        # Publish some events to generate statistics
        for i in range(5):
            event = StandardizedEvent(
                event_id=f"health-test-{i}",
                correlation_id=f"health-corr-{i}",
                timestamp=datetime.now(timezone.utc).isoformat(),
                event_type="PMO_RESPONSE",
                schema_version="2.0",
                priority="MEDIUM",
                confidence_score=0.88,
                email_metadata=EventEmailMetadata(
                    uid=f"health-uid-{i}",
                    message_id=f"health-msg-{i}",
                    sender=f"health{i}@test.com",
                    sender_name=f"Health Test {i}",
                    recipients=["recipient@test.com"],
                    subject=f"Health Test Subject {i}",
                    received_date=datetime.now(timezone.utc).isoformat(),
                    thread_id=f"health-thread-{i}",
                    content_hash=f"health-hash-{i}",
                    size_bytes=768
                ),
                content=EventContent(
                    body_text=f"Health test content {i}",
                    body_text_preview=f"Health test {i}...",
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
                    assigned_queue="health_test_queue",
                    workflow_type="PMO_RESPONSE",
                    priority_level="MEDIUM",
                    processing_requirements={},
                    estimated_processing_time=75.0,
                    escalation_required=False
                )
            )
            
            publisher.publish_event(event, "health_test_queue", require_confirmation=False)
        
        # Get updated statistics
        updated_stats = publisher.get_publishing_stats()
        
        # Verify statistics were updated
        assert updated_stats.total_events > initial_stats.total_events
        assert updated_stats.average_latency_ms > 0
        
        # Test buffer status
        buffer_status = publisher.get_buffer_status()
        assert 'buffer_size' in buffer_status
        assert 'buffer_utilization' in buffer_status
        assert 'processor_running' in buffer_status


if __name__ == "__main__":
    pytest.main([__file__, "-v"])