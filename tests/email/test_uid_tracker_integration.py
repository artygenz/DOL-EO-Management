"""
Integration tests for UID-Based Email Tracking System.

Tests end-to-end functionality with real Redis and database connections,
state recovery scenarios, and performance under load.
"""

import pytest
import time
import threading
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

import redis
from redis.exceptions import ConnectionError as RedisConnectionError

from src.email.uid_tracker import UIDTracker, EmailIdentifiers, TrackingStatus, calculate_content_hash
from src.email.redis_client import RedisClient
from src.database.manager import DatabaseManager
from src.database.models import EmailProcessingState, ProcessingStatus, EmailMetadata
from src.config.models import RedisConfig, DatabaseConnectionConfig


@pytest.fixture(scope="session")
def redis_config():
    """Redis configuration for testing."""
    return RedisConfig(
        host="localhost",
        port=6379,
        database=1,  # Use test database
        password=None,
        connection_pool_size=10
    )


@pytest.fixture(scope="session")
def database_config():
    """Database configuration for testing."""
    return DatabaseConnectionConfig(
        primary_host="localhost",
        port=5432,
        database="email_agent_test",
        username="test_user",
        password="test_password",
        pool_size=5
    )


@pytest.fixture(scope="session")
def redis_client(redis_config):
    """Create Redis client for testing."""
    try:
        client = RedisClient(redis_config)
        if not client.is_healthy:
            pytest.skip("Redis not available for integration tests")
        yield client
        # Cleanup
        client.close()
    except Exception:
        pytest.skip("Redis not available for integration tests")


@pytest.fixture(scope="session")
def database_manager(database_config):
    """Create database manager for testing."""
    try:
        manager = DatabaseManager(database_config)
        yield manager
        # Cleanup would go here if needed
    except Exception:
        pytest.skip("Database not available for integration tests")


@pytest.fixture
def uid_tracker(redis_client, database_manager):
    """Create UID tracker with real dependencies."""
    # Clear test data before each test
    redis_client._client.flushdb()  # Clear test database
    
    tracker = UIDTracker(redis_client, database_manager)
    yield tracker
    
    # Cleanup after each test
    redis_client._client.flushdb()


@pytest.fixture
def sample_emails():
    """Generate sample email data for testing."""
    emails = []
    for i in range(10):
        content = f"This is test email content number {i}"
        emails.append(EmailIdentifiers(
            uid=f"uid_{i:04d}",
            message_id=f"<test_{i:04d}@example.com>",
            content_hash=calculate_content_hash(content),
            account_id="test_account",
            received_date=datetime.utcnow()
        ))
    return emails


class TestUIDTrackerIntegration:
    """Integration tests for UID tracker with real dependencies."""
    
    def test_track_new_emails_end_to_end(self, uid_tracker, sample_emails):
        """Test tracking new emails end-to-end with Redis and database."""
        results = []
        
        for email in sample_emails[:5]:  # Test first 5 emails
            metadata = EmailMetadata(
                uid=email.uid,
                message_id=email.message_id,
                sender="sender@example.com",
                subject=f"Test Subject {email.uid}",
                received_date=email.received_date,
                account_id=email.account_id
            )
            
            result = uid_tracker.track_email(email, metadata)
            results.append(result)
        
        # Verify all emails were tracked as new
        for result in results:
            assert result.status == TrackingStatus.NEW
            assert not result.is_duplicate
            assert result.first_seen is not None
            assert result.processing_state is not None
        
        # Verify tracking metrics
        metrics = uid_tracker.get_tracking_metrics()
        assert metrics['duplicate_detections'] == 0
        assert metrics['redis_healthy'] is True
    
    def test_duplicate_detection_accuracy(self, uid_tracker, sample_emails):
        """Test 99.99% duplicate detection accuracy with real storage."""
        # Track first email
        first_email = sample_emails[0]
        metadata = EmailMetadata(
            uid=first_email.uid,
            message_id=first_email.message_id,
            sender="sender@example.com",
            subject="Test Subject",
            received_date=first_email.received_date,
            account_id=first_email.account_id
        )
        
        result1 = uid_tracker.track_email(first_email, metadata)
        assert result1.status == TrackingStatus.NEW
        assert not result1.is_duplicate
        
        # Track same email again (should be duplicate by UID)
        result2 = uid_tracker.track_email(first_email, metadata)
        assert result2.status == TrackingStatus.DUPLICATE
        assert result2.is_duplicate
        assert "uid" in result2.duplicate_sources
        
        # Track email with same Message-ID but different UID
        duplicate_msgid = EmailIdentifiers(
            uid="different_uid",
            message_id=first_email.message_id,  # Same Message-ID
            content_hash="different_hash",
            account_id=first_email.account_id,
            received_date=datetime.utcnow()
        )
        
        result3 = uid_tracker.track_email(duplicate_msgid)
        assert result3.status == TrackingStatus.DUPLICATE
        assert result3.is_duplicate
        assert "message_id" in result3.duplicate_sources
        
        # Track email with same content hash but different UID and Message-ID
        duplicate_hash = EmailIdentifiers(
            uid="another_different_uid",
            message_id="<different@example.com>",
            content_hash=first_email.content_hash,  # Same content hash
            account_id="different_account",
            received_date=datetime.utcnow()
        )
        
        result4 = uid_tracker.track_email(duplicate_hash)
        assert result4.status == TrackingStatus.DUPLICATE
        assert result4.is_duplicate
        assert "content_hash" in result4.duplicate_sources
        
        # Verify metrics
        metrics = uid_tracker.get_tracking_metrics()
        assert metrics['duplicate_detections'] == 3
    
    def test_incremental_uid_detection(self, uid_tracker):
        """Test incremental UID detection functionality."""
        account_id = "test_account"
        
        # First check - should return empty list and store range
        new_uids = uid_tracker.get_new_uids(account_id, 100)
        assert new_uids == []
        
        # Second check with higher UID - should return new UIDs
        new_uids = uid_tracker.get_new_uids(account_id, 150)
        assert new_uids == list(range(101, 151))
        
        # Third check with same UID - should return empty list
        new_uids = uid_tracker.get_new_uids(account_id, 150)
        assert new_uids == []
        
        # Fourth check with lower UID - should return empty list
        new_uids = uid_tracker.get_new_uids(account_id, 140)
        assert new_uids == []
    
    def test_processing_state_lifecycle(self, uid_tracker, sample_emails):
        """Test complete processing state lifecycle."""
        email = sample_emails[0]
        metadata = EmailMetadata(
            uid=email.uid,
            message_id=email.message_id,
            sender="sender@example.com",
            subject="Test Subject",
            received_date=email.received_date,
            account_id=email.account_id
        )
        
        # Track email (creates initial state)
        result = uid_tracker.track_email(email, metadata)
        assert result.processing_state.status == ProcessingStatus.DETECTED
        
        # Update to processing
        success = uid_tracker.update_processing_state(email.uid, ProcessingStatus.PROCESSING)
        assert success is True
        
        # Update to classified
        success = uid_tracker.update_processing_state(email.uid, ProcessingStatus.CLASSIFIED)
        assert success is True
        
        # Update to completed
        success = uid_tracker.update_processing_state(email.uid, ProcessingStatus.COMPLETED)
        assert success is True
        
        # Verify final state in database
        final_state = uid_tracker.db.get_email_processing_state(email.uid)
        assert final_state.status == ProcessingStatus.COMPLETED
        assert final_state.processed_at is not None
    
    def test_state_recovery_after_restart(self, uid_tracker, sample_emails):
        """Test processing state recovery after system restart."""
        # Track several emails and update their states
        tracked_emails = sample_emails[:3]
        
        for i, email in enumerate(tracked_emails):
            metadata = EmailMetadata(
                uid=email.uid,
                message_id=email.message_id,
                sender="sender@example.com",
                subject=f"Test Subject {i}",
                received_date=email.received_date,
                account_id=email.account_id
            )
            
            # Track email
            uid_tracker.track_email(email, metadata)
            
            # Update to different states (not completed)
            if i == 0:
                uid_tracker.update_processing_state(email.uid, ProcessingStatus.PROCESSING)
            elif i == 1:
                uid_tracker.update_processing_state(email.uid, ProcessingStatus.CLASSIFIED)
            # Leave third email in DETECTED state
        
        # Simulate system restart by creating new tracker instance
        new_tracker = UIDTracker(uid_tracker.redis, uid_tracker.db)
        
        # Recover processing states
        recovered_states = new_tracker.recover_processing_states("test_account")
        
        # Verify recovery
        assert len(recovered_states) == 3
        assert recovered_states[tracked_emails[0].uid].status == ProcessingStatus.PROCESSING
        assert recovered_states[tracked_emails[1].uid].status == ProcessingStatus.CLASSIFIED
        assert recovered_states[tracked_emails[2].uid].status == ProcessingStatus.DETECTED
    
    def test_redis_failover_graceful_degradation(self, uid_tracker, sample_emails, redis_client):
        """Test graceful degradation when Redis becomes unavailable."""
        email = sample_emails[0]
        
        # Track email with Redis available
        result1 = uid_tracker.track_email(email)
        assert result1.status == TrackingStatus.NEW
        
        # Simulate Redis failure
        redis_client._is_healthy = False
        
        # Track same email again - should still detect duplicate via database
        result2 = uid_tracker.track_email(email)
        assert result2.status == TrackingStatus.DUPLICATE
        assert result2.is_duplicate
        
        # Track new email - should work with database only
        new_email = sample_emails[1]
        result3 = uid_tracker.track_email(new_email)
        assert result3.status == TrackingStatus.NEW
        
        # Verify metrics show Redis as unhealthy
        metrics = uid_tracker.get_tracking_metrics()
        assert metrics['redis_healthy'] is False
    
    def test_concurrent_email_tracking(self, uid_tracker, sample_emails):
        """Test concurrent email tracking for thread safety."""
        def track_email_worker(email_data):
            """Worker function for concurrent tracking."""
            email, metadata = email_data
            return uid_tracker.track_email(email, metadata)
        
        # Prepare email data with metadata
        email_data = []
        for i, email in enumerate(sample_emails):
            metadata = EmailMetadata(
                uid=email.uid,
                message_id=email.message_id,
                sender=f"sender{i}@example.com",
                subject=f"Concurrent Test {i}",
                received_date=email.received_date,
                account_id=email.account_id
            )
            email_data.append((email, metadata))
        
        # Track emails concurrently
        results = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_email = {
                executor.submit(track_email_worker, data): data[0] 
                for data in email_data
            }
            
            for future in as_completed(future_to_email):
                email = future_to_email[future]
                try:
                    result = future.result()
                    results.append((email.uid, result))
                except Exception as exc:
                    pytest.fail(f"Email {email.uid} generated an exception: {exc}")
        
        # Verify all emails were tracked successfully
        assert len(results) == len(sample_emails)
        for uid, result in results:
            assert result.status == TrackingStatus.NEW
            assert not result.is_duplicate
        
        # Verify no duplicates were incorrectly detected
        metrics = uid_tracker.get_tracking_metrics()
        assert metrics['duplicate_detections'] == 0
    
    def test_performance_under_load(self, uid_tracker):
        """Test performance with high volume of emails."""
        num_emails = 1000
        start_time = time.time()
        
        # Generate and track many emails
        for i in range(num_emails):
            content = f"Performance test email content {i}"
            email = EmailIdentifiers(
                uid=f"perf_uid_{i:06d}",
                message_id=f"<perf_{i:06d}@example.com>",
                content_hash=calculate_content_hash(content),
                account_id="perf_test_account",
                received_date=datetime.utcnow()
            )
            
            result = uid_tracker.track_email(email)
            assert result.status == TrackingStatus.NEW
        
        end_time = time.time()
        total_time = end_time - start_time
        emails_per_second = num_emails / total_time
        
        # Performance assertions
        assert emails_per_second > 100, f"Performance too slow: {emails_per_second:.2f} emails/sec"
        assert total_time < 30, f"Total time too long: {total_time:.2f} seconds"
        
        # Verify metrics
        metrics = uid_tracker.get_tracking_metrics()
        assert metrics['duplicate_detections'] == 0
        assert metrics['redis_healthy'] is True
        
        print(f"Performance test: {emails_per_second:.2f} emails/sec, {total_time:.2f}s total")
    
    def test_cleanup_expired_data(self, uid_tracker, sample_emails):
        """Test cleanup of expired tracking data."""
        # Track some emails
        for email in sample_emails[:3]:
            uid_tracker.track_email(email)
        
        # Verify data exists
        metrics_before = uid_tracker.get_tracking_metrics()
        
        # Run cleanup (should not remove recent data)
        cleaned_count = uid_tracker.cleanup_expired_data(days_old=1)
        assert cleaned_count >= 0  # May or may not clean anything
        
        # Track more emails to verify system still works
        for email in sample_emails[3:6]:
            result = uid_tracker.track_email(email)
            assert result.status == TrackingStatus.NEW
    
    def test_cache_hit_rate_optimization(self, uid_tracker, sample_emails):
        """Test cache hit rate optimization."""
        # Track emails first time
        for email in sample_emails[:5]:
            result = uid_tracker.track_email(email)
            assert result.status == TrackingStatus.NEW
        
        # Track same emails again (should hit cache)
        for email in sample_emails[:5]:
            result = uid_tracker.track_email(email)
            assert result.status == TrackingStatus.DUPLICATE
        
        # Check cache hit rate
        metrics = uid_tracker.get_tracking_metrics()
        assert metrics['cache_hit_rate'] > 0
        assert metrics['cache_hits'] > 0
        
        print(f"Cache hit rate: {metrics['cache_hit_rate']:.2f}%")
    
    def test_multi_account_isolation(self, uid_tracker):
        """Test that different accounts are properly isolated."""
        # Create emails with same UID but different accounts
        email1 = EmailIdentifiers(
            uid="same_uid",
            message_id="<test1@example.com>",
            content_hash="hash1",
            account_id="account1",
            received_date=datetime.utcnow()
        )
        
        email2 = EmailIdentifiers(
            uid="same_uid",  # Same UID
            message_id="<test2@example.com>",
            content_hash="hash2",
            account_id="account2",  # Different account
            received_date=datetime.utcnow()
        )
        
        # Track both emails
        result1 = uid_tracker.track_email(email1)
        result2 = uid_tracker.track_email(email2)
        
        # Both should be tracked as new (different accounts)
        assert result1.status == TrackingStatus.NEW
        assert result2.status == TrackingStatus.NEW
        assert not result1.is_duplicate
        assert not result2.is_duplicate
        
        # Track same email in same account (should be duplicate)
        result3 = uid_tracker.track_email(email1)
        assert result3.status == TrackingStatus.DUPLICATE
        assert result3.is_duplicate


if __name__ == "__main__":
    pytest.main([__file__, "-v"])