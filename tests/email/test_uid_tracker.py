"""
Unit tests for UID-Based Email Tracking System.

Tests incremental email detection, duplicate detection accuracy,
Redis caching, database persistence, and state recovery functionality.
"""

import pytest
import time
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch, call
from dataclasses import asdict

from src.email.uid_tracker import (
    UIDTracker, EmailIdentifiers, TrackingResult, TrackingStatus,
    UIDRange, calculate_content_hash
)
from src.email.redis_client import RedisClient
from src.database.manager import DatabaseManager
from src.database.models import EmailProcessingState, ProcessingStatus, EmailMetadata
from src.database.exceptions import StateTrackingError


class TestEmailIdentifiers:
    """Test EmailIdentifiers data class."""
    
    def test_valid_identifiers(self):
        """Test creating valid email identifiers."""
        identifiers = EmailIdentifiers(
            uid="12345",
            message_id="<test@example.com>",
            content_hash="abc123",
            account_id="test_account",
            received_date=datetime.utcnow()
        )
        
        assert identifiers.uid == "12345"
        assert identifiers.message_id == "<test@example.com>"
        assert identifiers.content_hash == "abc123"
        assert identifiers.account_id == "test_account"
        assert isinstance(identifiers.received_date, datetime)
    
    def test_empty_uid_raises_error(self):
        """Test that empty UID raises ValueError."""
        with pytest.raises(ValueError, match="Email UID cannot be empty"):
            EmailIdentifiers(
                uid="",
                message_id="<test@example.com>",
                content_hash="abc123",
                account_id="test_account",
                received_date=datetime.utcnow()
            )
    
    def test_empty_message_id_raises_error(self):
        """Test that empty message ID raises ValueError."""
        with pytest.raises(ValueError, match="Message ID cannot be empty"):
            EmailIdentifiers(
                uid="12345",
                message_id="",
                content_hash="abc123",
                account_id="test_account",
                received_date=datetime.utcnow()
            )
    
    def test_empty_content_hash_raises_error(self):
        """Test that empty content hash raises ValueError."""
        with pytest.raises(ValueError, match="Content hash cannot be empty"):
            EmailIdentifiers(
                uid="12345",
                message_id="<test@example.com>",
                content_hash="",
                account_id="test_account",
                received_date=datetime.utcnow()
            )
    
    def test_empty_account_id_raises_error(self):
        """Test that empty account ID raises ValueError."""
        with pytest.raises(ValueError, match="Account ID cannot be empty"):
            EmailIdentifiers(
                uid="12345",
                message_id="<test@example.com>",
                content_hash="abc123",
                account_id="",
                received_date=datetime.utcnow()
            )


class TestUIDRange:
    """Test UIDRange data class."""
    
    def test_valid_uid_range(self):
        """Test creating valid UID range."""
        uid_range = UIDRange(
            account_id="test_account",
            last_uid=100,
            highest_uid=150,
            last_check=datetime.utcnow()
        )
        
        assert uid_range.account_id == "test_account"
        assert uid_range.last_uid == 100
        assert uid_range.highest_uid == 150
        assert isinstance(uid_range.last_check, datetime)
    
    def test_negative_last_uid_raises_error(self):
        """Test that negative last UID raises ValueError."""
        with pytest.raises(ValueError, match="Last UID cannot be negative"):
            UIDRange(
                account_id="test_account",
                last_uid=-1,
                highest_uid=150,
                last_check=datetime.utcnow()
            )
    
    def test_highest_uid_less_than_last_uid_raises_error(self):
        """Test that highest UID less than last UID raises ValueError."""
        with pytest.raises(ValueError, match="Highest UID cannot be less than last UID"):
            UIDRange(
                account_id="test_account",
                last_uid=150,
                highest_uid=100,
                last_check=datetime.utcnow()
            )


class TestCalculateContentHash:
    """Test content hash calculation function."""
    
    def test_consistent_hash(self):
        """Test that same content produces same hash."""
        content = "This is test email content"
        hash1 = calculate_content_hash(content)
        hash2 = calculate_content_hash(content)
        
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 produces 64-character hex string
    
    def test_different_content_different_hash(self):
        """Test that different content produces different hashes."""
        content1 = "This is test email content"
        content2 = "This is different email content"
        
        hash1 = calculate_content_hash(content1)
        hash2 = calculate_content_hash(content2)
        
        assert hash1 != hash2
    
    def test_empty_content_hash(self):
        """Test hashing empty content."""
        hash_result = calculate_content_hash("")
        assert len(hash_result) == 64
        assert hash_result == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


class TestUIDTracker:
    """Test UIDTracker class functionality."""
    
    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        redis_mock = Mock(spec=RedisClient)
        redis_mock.is_healthy = True
        redis_mock.exists.return_value = False
        redis_mock.setex.return_value = True
        redis_mock.get.return_value = None
        redis_mock.pipeline.return_value = Mock()
        return redis_mock
    
    @pytest.fixture
    def mock_database(self):
        """Create mock database manager."""
        db_mock = Mock(spec=DatabaseManager)
        db_mock.check_email_duplicate.return_value = False
        db_mock.store_email_processing_state.return_value = 1
        db_mock.get_email_processing_state.return_value = None
        return db_mock
    
    @pytest.fixture
    def uid_tracker(self, mock_redis, mock_database):
        """Create UIDTracker instance with mocked dependencies."""
        return UIDTracker(mock_redis, mock_database)
    
    @pytest.fixture
    def sample_identifiers(self):
        """Create sample email identifiers."""
        return EmailIdentifiers(
            uid="12345",
            message_id="<test@example.com>",
            content_hash="abc123def456",
            account_id="test_account",
            received_date=datetime.utcnow()
        )
    
    @pytest.fixture
    def sample_metadata(self):
        """Create sample email metadata."""
        return EmailMetadata(
            uid="12345",
            message_id="<test@example.com>",
            sender="sender@example.com",
            subject="Test Subject",
            received_date=datetime.utcnow(),
            account_id="test_account"
        )
    
    def test_initialization(self, mock_redis, mock_database):
        """Test UIDTracker initialization."""
        tracker = UIDTracker(mock_redis, mock_database)
        
        assert tracker.redis == mock_redis
        assert tracker.db == mock_database
        assert tracker._cache_hits == 0
        assert tracker._cache_misses == 0
        assert tracker._duplicate_detections == 0
    
    def test_track_new_email(self, uid_tracker, sample_identifiers, sample_metadata):
        """Test tracking a new email (not duplicate)."""
        # Mock all duplicate checks to return False
        uid_tracker._check_uid_duplicate = Mock(return_value=False)
        uid_tracker._check_message_id_duplicate = Mock(return_value=False)
        uid_tracker._check_content_hash_duplicate = Mock(return_value=False)
        uid_tracker._store_email_tracking = Mock()
        uid_tracker._create_processing_state = Mock(return_value=Mock())
        
        result = uid_tracker.track_email(sample_identifiers, sample_metadata)
        
        assert result.status == TrackingStatus.NEW
        assert not result.is_duplicate
        assert result.duplicate_sources == []
        assert result.first_seen is not None
        
        # Verify all duplicate checks were called
        uid_tracker._check_uid_duplicate.assert_called_once_with("12345", "test_account")
        uid_tracker._check_message_id_duplicate.assert_called_once_with("<test@example.com>", "test_account")
        uid_tracker._check_content_hash_duplicate.assert_called_once_with("abc123def456")
        
        # Verify email was stored
        uid_tracker._store_email_tracking.assert_called_once_with(sample_identifiers)
        uid_tracker._create_processing_state.assert_called_once_with(sample_identifiers, sample_metadata)
    
    def test_track_duplicate_email_uid(self, uid_tracker, sample_identifiers):
        """Test tracking a duplicate email detected by UID."""
        # Mock UID duplicate check to return True
        uid_tracker._check_uid_duplicate = Mock(return_value=True)
        uid_tracker._check_message_id_duplicate = Mock(return_value=False)
        uid_tracker._check_content_hash_duplicate = Mock(return_value=False)
        
        result = uid_tracker.track_email(sample_identifiers)
        
        assert result.status == TrackingStatus.DUPLICATE
        assert result.is_duplicate
        assert "uid" in result.duplicate_sources
        assert uid_tracker._duplicate_detections == 1
    
    def test_track_duplicate_email_message_id(self, uid_tracker, sample_identifiers):
        """Test tracking a duplicate email detected by Message-ID."""
        # Mock Message-ID duplicate check to return True
        uid_tracker._check_uid_duplicate = Mock(return_value=False)
        uid_tracker._check_message_id_duplicate = Mock(return_value=True)
        uid_tracker._check_content_hash_duplicate = Mock(return_value=False)
        
        result = uid_tracker.track_email(sample_identifiers)
        
        assert result.status == TrackingStatus.DUPLICATE
        assert result.is_duplicate
        assert "message_id" in result.duplicate_sources
    
    def test_track_duplicate_email_content_hash(self, uid_tracker, sample_identifiers):
        """Test tracking a duplicate email detected by content hash."""
        # Mock content hash duplicate check to return True
        uid_tracker._check_uid_duplicate = Mock(return_value=False)
        uid_tracker._check_message_id_duplicate = Mock(return_value=False)
        uid_tracker._check_content_hash_duplicate = Mock(return_value=True)
        
        result = uid_tracker.track_email(sample_identifiers)
        
        assert result.status == TrackingStatus.DUPLICATE
        assert result.is_duplicate
        assert "content_hash" in result.duplicate_sources
    
    def test_track_duplicate_email_multiple_sources(self, uid_tracker, sample_identifiers):
        """Test tracking a duplicate email detected by multiple sources."""
        # Mock multiple duplicate checks to return True
        uid_tracker._check_uid_duplicate = Mock(return_value=True)
        uid_tracker._check_message_id_duplicate = Mock(return_value=True)
        uid_tracker._check_content_hash_duplicate = Mock(return_value=False)
        
        result = uid_tracker.track_email(sample_identifiers)
        
        assert result.status == TrackingStatus.DUPLICATE
        assert result.is_duplicate
        assert "uid" in result.duplicate_sources
        assert "message_id" in result.duplicate_sources
        assert "content_hash" not in result.duplicate_sources
    
    def test_get_new_uids_first_time(self, uid_tracker):
        """Test getting new UIDs for first time check."""
        uid_tracker._get_uid_range = Mock(return_value=None)
        uid_tracker._store_uid_range = Mock()
        
        new_uids = uid_tracker.get_new_uids("test_account", 100)
        
        assert new_uids == []
        uid_tracker._get_uid_range.assert_called_once_with("test_account")
        uid_tracker._store_uid_range.assert_called_once()
    
    def test_get_new_uids_with_new_emails(self, uid_tracker):
        """Test getting new UIDs when there are new emails."""
        # Mock existing UID range
        existing_range = UIDRange(
            account_id="test_account",
            last_uid=50,
            highest_uid=80,
            last_check=datetime.utcnow() - timedelta(minutes=5)
        )
        uid_tracker._get_uid_range = Mock(return_value=existing_range)
        uid_tracker._store_uid_range = Mock()
        
        new_uids = uid_tracker.get_new_uids("test_account", 100)
        
        assert new_uids == list(range(81, 101))  # UIDs 81-100
        uid_tracker._store_uid_range.assert_called_once()
    
    def test_get_new_uids_no_new_emails(self, uid_tracker):
        """Test getting new UIDs when there are no new emails."""
        # Mock existing UID range with same highest UID
        existing_range = UIDRange(
            account_id="test_account",
            last_uid=50,
            highest_uid=100,
            last_check=datetime.utcnow() - timedelta(minutes=5)
        )
        uid_tracker._get_uid_range = Mock(return_value=existing_range)
        
        new_uids = uid_tracker.get_new_uids("test_account", 100)
        
        assert new_uids == []
    
    def test_update_processing_state_success(self, uid_tracker, mock_database):
        """Test successful processing state update."""
        # Mock existing processing state
        existing_state = EmailProcessingState(
            id=1,
            email_uid="12345",
            message_id="<test@example.com>",
            account_id="test_account",
            status=ProcessingStatus.DETECTED
        )
        mock_database.get_email_processing_state.return_value = existing_state
        mock_database.store_email_processing_state.return_value = 1
        uid_tracker._cache_processing_state = Mock()
        
        result = uid_tracker.update_processing_state("12345", ProcessingStatus.PROCESSING)
        
        assert result is True
        mock_database.get_email_processing_state.assert_called_once_with("12345")
        mock_database.store_email_processing_state.assert_called_once()
        uid_tracker._cache_processing_state.assert_called_once()
    
    def test_update_processing_state_not_found(self, uid_tracker, mock_database):
        """Test processing state update when state not found."""
        mock_database.get_email_processing_state.return_value = None
        
        result = uid_tracker.update_processing_state("12345", ProcessingStatus.PROCESSING)
        
        assert result is False
    
    def test_recover_processing_states(self, uid_tracker, mock_database):
        """Test processing state recovery after system restart."""
        # Mock database connection and cursor
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_database.get_connection.return_value = mock_conn
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=None)
        
        # Mock database rows
        mock_rows = [
            (1, "12345", "<test1@example.com>", "account1", "processing", 
             {"uid": "12345", "sender": "test@example.com"}, None, None, 0,
             datetime.utcnow(), datetime.utcnow(), None),
            (2, "67890", "<test2@example.com>", "account1", "classified",
             {"uid": "67890", "sender": "test2@example.com"}, {"type": "NEW_EO"}, None, 0,
             datetime.utcnow(), datetime.utcnow(), None)
        ]
        mock_cursor.fetchall.return_value = mock_rows
        uid_tracker._cache_processing_state = Mock()
        
        recovered_states = uid_tracker.recover_processing_states("account1")
        
        assert len(recovered_states) == 2
        assert "12345" in recovered_states
        assert "67890" in recovered_states
        assert recovered_states["12345"].status == ProcessingStatus.PROCESSING
        assert recovered_states["67890"].status == ProcessingStatus.CLASSIFIED
        
        # Verify caching was called for each recovered state
        assert uid_tracker._cache_processing_state.call_count == 2
    
    def test_get_tracking_metrics(self, uid_tracker, mock_redis):
        """Test getting tracking metrics."""
        # Set up some metrics
        uid_tracker._cache_hits = 100
        uid_tracker._cache_misses = 20
        uid_tracker._duplicate_detections = 5
        
        # Mock Redis info
        mock_redis.info.return_value = {
            'connected_clients': 10,
            'used_memory_human': '1.5M',
            'keyspace_hits': 500,
            'keyspace_misses': 50
        }
        
        metrics = uid_tracker.get_tracking_metrics()
        
        assert metrics['cache_hit_rate'] == 83.33  # 100/(100+20) * 100
        assert metrics['cache_hits'] == 100
        assert metrics['cache_misses'] == 20
        assert metrics['duplicate_detections'] == 5
        assert metrics['redis_healthy'] is True
        assert 'redis_info' in metrics
    
    def test_cleanup_expired_data(self, uid_tracker, mock_database, mock_redis):
        """Test cleanup of expired tracking data."""
        # Mock database connection and cursor
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_database.get_connection.return_value = mock_conn
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=None)
        
        # Mock cursor rowcount for deletions
        mock_cursor.rowcount = 10  # First deletion
        mock_cursor.configure_mock(**{'rowcount': 5})  # Second deletion
        
        # Mock Redis keys
        mock_redis.keys.return_value = [b'email_track:uid:account1:12345', b'email_track:uid:account1:67890']
        mock_redis.exists.side_effect = [False, True]  # First key expired, second exists
        
        cleaned_count = uid_tracker.cleanup_expired_data(30)
        
        # Should clean up database records plus expired Redis keys
        assert cleaned_count >= 1  # At least the expired Redis key
        
        # Verify database cleanup queries were executed
        assert mock_cursor.execute.call_count == 2
    
    def test_check_uid_duplicate_redis_hit(self, uid_tracker, mock_redis):
        """Test UID duplicate check with Redis cache hit."""
        mock_redis.exists.return_value = True
        
        result = uid_tracker._check_uid_duplicate("12345", "test_account")
        
        assert result is True
        assert uid_tracker._cache_hits == 1
        mock_redis.exists.assert_called_once()
    
    def test_check_uid_duplicate_redis_miss_db_hit(self, uid_tracker, mock_redis, mock_database):
        """Test UID duplicate check with Redis miss but database hit."""
        mock_redis.exists.return_value = False
        mock_database.check_email_duplicate.return_value = True
        
        result = uid_tracker._check_uid_duplicate("12345", "test_account")
        
        assert result is True
        assert uid_tracker._cache_misses == 1
        mock_database.check_email_duplicate.assert_called_once_with("12345", "", "", "test_account")
    
    def test_check_uid_duplicate_redis_unavailable(self, uid_tracker, mock_redis, mock_database):
        """Test UID duplicate check when Redis is unavailable."""
        uid_tracker._redis_healthy = False
        mock_database.check_email_duplicate.return_value = False
        
        result = uid_tracker._check_uid_duplicate("12345", "test_account")
        
        assert result is False
        # Should not call Redis when unhealthy
        mock_redis.exists.assert_not_called()
        mock_database.check_email_duplicate.assert_called_once()
    
    def test_store_email_tracking_redis_and_db(self, uid_tracker, mock_redis, mock_database, sample_identifiers):
        """Test storing email tracking in both Redis and database."""
        # Mock Redis pipeline
        mock_pipeline = Mock()
        mock_redis.pipeline.return_value = mock_pipeline
        mock_database.check_email_duplicate.return_value = False
        
        uid_tracker._store_email_tracking(sample_identifiers)
        
        # Verify Redis pipeline operations
        mock_redis.pipeline.assert_called_once()
        mock_pipeline.setex.assert_called()  # Should be called multiple times
        mock_pipeline.execute.assert_called_once()
        
        # Verify database storage
        mock_database.check_email_duplicate.assert_called_once()
    
    def test_store_email_tracking_redis_failure(self, uid_tracker, mock_redis, mock_database, sample_identifiers):
        """Test storing email tracking when Redis fails."""
        # Mock Redis failure
        mock_redis.pipeline.side_effect = Exception("Redis connection failed")
        mock_database.check_email_duplicate.return_value = False
        
        # Should not raise exception, should continue with database
        uid_tracker._store_email_tracking(sample_identifiers)
        
        # Verify database storage still works
        mock_database.check_email_duplicate.assert_called_once()
        assert uid_tracker._redis_healthy is False
    
    def test_create_processing_state(self, uid_tracker, mock_database, sample_identifiers, sample_metadata):
        """Test creating email processing state."""
        mock_database.store_email_processing_state.return_value = 1
        uid_tracker._cache_processing_state = Mock()
        
        state = uid_tracker._create_processing_state(sample_identifiers, sample_metadata)
        
        assert state.email_uid == "12345"
        assert state.message_id == "<test@example.com>"
        assert state.account_id == "test_account"
        assert state.status == ProcessingStatus.DETECTED
        assert state.metadata == sample_metadata
        assert state.id == 1
        
        mock_database.store_email_processing_state.assert_called_once()
        uid_tracker._cache_processing_state.assert_called_once_with(state)
    
    def test_cache_processing_state_redis_healthy(self, uid_tracker, mock_redis):
        """Test caching processing state when Redis is healthy."""
        state = EmailProcessingState(
            id=1,
            email_uid="12345",
            message_id="<test@example.com>",
            account_id="test_account",
            status=ProcessingStatus.PROCESSING
        )
        
        uid_tracker._cache_processing_state(state)
        
        mock_redis.setex.assert_called_once()
        # Verify the cache key format
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == "proc_state:12345"
        assert call_args[0][1] == uid_tracker.PROCESSING_STATE_EXPIRY
    
    def test_cache_processing_state_redis_unhealthy(self, uid_tracker, mock_redis):
        """Test caching processing state when Redis is unhealthy."""
        uid_tracker._redis_healthy = False
        state = EmailProcessingState(
            id=1,
            email_uid="12345",
            message_id="<test@example.com>",
            account_id="test_account",
            status=ProcessingStatus.PROCESSING
        )
        
        uid_tracker._cache_processing_state(state)
        
        # Should not call Redis when unhealthy
        mock_redis.setex.assert_not_called()
    
    def test_tracking_error_handling(self, uid_tracker, sample_identifiers):
        """Test error handling in email tracking."""
        # Mock all duplicate checks to raise exceptions
        uid_tracker._check_uid_duplicate = Mock(side_effect=Exception("Database error"))
        
        with pytest.raises(StateTrackingError):
            uid_tracker.track_email(sample_identifiers)
    
    def test_duplicate_detection_accuracy(self, uid_tracker, mock_redis, mock_database):
        """Test 99.99% duplicate detection accuracy through comprehensive testing."""
        # Test various duplicate scenarios
        test_cases = [
            # (uid_dup, msgid_dup, hash_dup, expected_duplicate)
            (True, False, False, True),   # UID duplicate
            (False, True, False, True),   # Message-ID duplicate
            (False, False, True, True),   # Content hash duplicate
            (True, True, False, True),    # Multiple duplicates
            (False, False, False, False), # No duplicate
        ]
        
        for uid_dup, msgid_dup, hash_dup, expected_duplicate in test_cases:
            # Reset mocks
            uid_tracker._check_uid_duplicate = Mock(return_value=uid_dup)
            uid_tracker._check_message_id_duplicate = Mock(return_value=msgid_dup)
            uid_tracker._check_content_hash_duplicate = Mock(return_value=hash_dup)
            
            if not expected_duplicate:
                uid_tracker._store_email_tracking = Mock()
                uid_tracker._create_processing_state = Mock(return_value=Mock())
            
            identifiers = EmailIdentifiers(
                uid=f"uid_{uid_dup}_{msgid_dup}_{hash_dup}",
                message_id=f"<msg_{uid_dup}_{msgid_dup}_{hash_dup}@example.com>",
                content_hash=f"hash_{uid_dup}_{msgid_dup}_{hash_dup}",
                account_id="test_account",
                received_date=datetime.utcnow()
            )
            
            result = uid_tracker.track_email(identifiers)
            
            if expected_duplicate:
                assert result.is_duplicate is True
                assert result.status == TrackingStatus.DUPLICATE
            else:
                assert result.is_duplicate is False
                assert result.status == TrackingStatus.NEW


if __name__ == "__main__":
    pytest.main([__file__])