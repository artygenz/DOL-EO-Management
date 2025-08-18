"""
Comprehensive tests for Multi-Layer Deduplication System.

Tests all three layers of deduplication:
1. UID-based duplicate detection with Redis caching
2. Message-ID comparison with database persistence
3. SHA-256 content hash verification

Validates 99.99% accuracy requirement across all layers.
"""

import pytest
import time
import hashlib
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any

import redis
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError

from src.email.deduplication_handler import (
    MultiLayerDeduplicationHandler,
    EmailIdentifiers,
    DeduplicationResult,
    DeduplicationStats,
    DuplicateSource,
    calculate_content_hash,
    create_email_identifiers
)
from src.database.manager import DatabaseManager
from src.database.exceptions import DatabaseError


class TestEmailIdentifiers:
    """Test EmailIdentifiers data class."""
    
    def test_valid_email_identifiers(self):
        """Test creating valid email identifiers."""
        received_date = datetime.utcnow()
        content_hash = "a" * 64  # Valid SHA-256 hash
        
        identifiers = EmailIdentifiers(
            uid="12345",
            message_id="<test@example.com>",
            content_hash=content_hash,
            account_id="test_account",
            received_date=received_date,
            sender="sender@example.com",
            subject="Test Subject"
        )
        
        assert identifiers.uid == "12345"
        assert identifiers.message_id == "<test@example.com>"
        assert identifiers.content_hash == content_hash
        assert identifiers.account_id == "test_account"
        assert identifiers.received_date == received_date
        assert identifiers.sender == "sender@example.com"
        assert identifiers.subject == "Test Subject"
    
    def test_empty_uid_raises_error(self):
        """Test that empty UID raises ValueError."""
        with pytest.raises(ValueError, match="Email UID cannot be empty"):
            EmailIdentifiers(
                uid="",
                message_id="<test@example.com>",
                content_hash="a" * 64,
                account_id="test_account",
                received_date=datetime.utcnow()
            )
    
    def test_empty_message_id_raises_error(self):
        """Test that empty message ID raises ValueError."""
        with pytest.raises(ValueError, match="Message ID cannot be empty"):
            EmailIdentifiers(
                uid="12345",
                message_id="",
                content_hash="a" * 64,
                account_id="test_account",
                received_date=datetime.utcnow()
            )
    
    def test_invalid_content_hash_raises_error(self):
        """Test that invalid content hash raises ValueError."""
        with pytest.raises(ValueError, match="Content hash must be SHA-256"):
            EmailIdentifiers(
                uid="12345",
                message_id="<test@example.com>",
                content_hash="invalid_hash",
                account_id="test_account",
                received_date=datetime.utcnow()
            )
    
    def test_empty_account_id_raises_error(self):
        """Test that empty account ID raises ValueError."""
        with pytest.raises(ValueError, match="Account ID cannot be empty"):
            EmailIdentifiers(
                uid="12345",
                message_id="<test@example.com>",
                content_hash="a" * 64,
                account_id="",
                received_date=datetime.utcnow()
            )


class TestDeduplicationResult:
    """Test DeduplicationResult data class."""
    
    def test_non_duplicate_result(self):
        """Test non-duplicate result with high confidence."""
        result = DeduplicationResult(
            is_duplicate=False,
            duplicate_sources=[]
        )
        
        assert not result.is_duplicate
        assert result.duplicate_sources == []
        assert result.confidence_score == 0.9999  # 99.99% confidence
    
    def test_single_source_duplicate(self):
        """Test duplicate with single source."""
        result = DeduplicationResult(
            is_duplicate=True,
            duplicate_sources=[DuplicateSource.UID]
        )
        
        assert result.is_duplicate
        assert result.duplicate_sources == [DuplicateSource.UID]
        assert result.confidence_score == 0.965  # 95% + 1.5% bonus
    
    def test_multi_source_duplicate(self):
        """Test duplicate with multiple sources for higher confidence."""
        result = DeduplicationResult(
            is_duplicate=True,
            duplicate_sources=[DuplicateSource.UID, DuplicateSource.MESSAGE_ID, DuplicateSource.CONTENT_HASH]
        )
        
        assert result.is_duplicate
        assert len(result.duplicate_sources) == 3
        assert result.confidence_score == 0.995  # 95% + 3 * 1.5% bonus


class TestContentHashCalculation:
    """Test content hash calculation functions."""
    
    def test_calculate_content_hash_basic(self):
        """Test basic content hash calculation."""
        content = "This is test email content"
        hash_result = calculate_content_hash(content)
        
        assert len(hash_result) == 64  # SHA-256 hex length
        assert hash_result == hashlib.sha256(content.lower().strip().encode('utf-8')).hexdigest()
    
    def test_calculate_content_hash_normalization(self):
        """Test content normalization in hash calculation."""
        content1 = "This  is   test\n\n  content"
        content2 = "This is test content"
        
        hash1 = calculate_content_hash(content1, normalize=True)
        hash2 = calculate_content_hash(content2, normalize=True)
        
        assert hash1 == hash2  # Should be same after normalization
    
    def test_calculate_content_hash_no_normalization(self):
        """Test content hash without normalization."""
        content1 = "This  is   test\n\n  content"
        content2 = "This is test content"
        
        hash1 = calculate_content_hash(content1, normalize=False)
        hash2 = calculate_content_hash(content2, normalize=False)
        
        assert hash1 != hash2  # Should be different without normalization
    
    def test_create_email_identifiers_helper(self):
        """Test create_email_identifiers helper function."""
        uid = "12345"
        message_id = "<test@example.com>"
        content = "Test email content"
        account_id = "test_account"
        received_date = datetime.utcnow()
        sender = "sender@example.com"
        subject = "Test Subject"
        
        identifiers = create_email_identifiers(
            uid, message_id, content, account_id, received_date, sender, subject
        )
        
        assert identifiers.uid == uid
        assert identifiers.message_id == message_id
        assert identifiers.account_id == account_id
        assert identifiers.received_date == received_date
        assert identifiers.sender == sender
        assert identifiers.subject == subject
        assert len(identifiers.content_hash) == 64


class TestMultiLayerDeduplicationHandler:
    """Test the main deduplication handler."""
    
    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        mock_redis = Mock(spec=redis.Redis)
        mock_redis.get.return_value = None
        mock_redis.setex.return_value = True
        mock_redis.exists.return_value = False
        mock_redis.pipeline.return_value = Mock()
        mock_redis.info.return_value = {
            'keyspace_hits': 100,
            'keyspace_misses': 10
        }
        return mock_redis
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database manager."""
        mock_db = Mock(spec=DatabaseManager)
        
        # Create proper context manager mocks
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        
        # Set up context manager behavior
        mock_connection.__enter__ = Mock(return_value=mock_connection)
        mock_connection.__exit__ = Mock(return_value=None)
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        
        # Set up method returns
        mock_connection.cursor.return_value = mock_cursor
        mock_db.get_connection.return_value = mock_connection
        mock_cursor.fetchone.return_value = None
        mock_cursor.rowcount = 0
        
        return mock_db
    
    @pytest.fixture
    def dedup_handler(self, mock_redis, mock_db):
        """Create deduplication handler with mocked dependencies."""
        return MultiLayerDeduplicationHandler(mock_redis, mock_db)
    
    @pytest.fixture
    def sample_email_identifiers(self):
        """Create sample email identifiers for testing."""
        return EmailIdentifiers(
            uid="12345",
            message_id="<test@example.com>",
            content_hash=calculate_content_hash("Test email content"),
            account_id="test_account",
            received_date=datetime.utcnow(),
            sender="sender@example.com",
            subject="Test Subject"
        )
    
    def test_initialization(self, mock_redis, mock_db):
        """Test handler initialization."""
        handler = MultiLayerDeduplicationHandler(mock_redis, mock_db)
        
        assert handler.redis == mock_redis
        assert handler.db == mock_db
        assert handler._redis_healthy is True
        assert handler._db_healthy is True
        assert isinstance(handler._stats, DeduplicationStats)
    
    def test_check_duplicate_new_email(self, dedup_handler, sample_email_identifiers, mock_redis, mock_db):
        """Test duplicate check for new email (should not be duplicate)."""
        # Mock Redis and database to return no duplicates
        mock_redis.get.return_value = None
        
        result = dedup_handler.check_duplicate(sample_email_identifiers)
        
        assert not result.is_duplicate
        assert result.duplicate_sources == []
        assert result.confidence_score == 0.9999
        assert result.processing_time_ms > 0
    
    def test_check_duplicate_uid_duplicate(self, dedup_handler, sample_email_identifiers, mock_redis, mock_db):
        """Test duplicate detection via UID."""
        # Mock Redis to return UID duplicate
        first_seen = datetime.utcnow() - timedelta(hours=1)
        cache_data = {
            'first_seen': first_seen.isoformat(),
            'count': 2
        }
        mock_redis.get.side_effect = [json.dumps(cache_data), None, None]
        
        result = dedup_handler.check_duplicate(sample_email_identifiers)
        
        assert result.is_duplicate
        assert DuplicateSource.UID in result.duplicate_sources
        assert result.first_seen == first_seen
        assert result.duplicate_count == 2
    
    def test_check_duplicate_message_id_duplicate(self, dedup_handler, sample_email_identifiers, mock_redis, mock_db):
        """Test duplicate detection via Message-ID."""
        # Mock database to return Message-ID duplicate
        first_seen = datetime.utcnow() - timedelta(hours=2)
        mock_redis.get.side_effect = [None, json.dumps({
            'first_seen': first_seen.isoformat(),
            'count': 1
        }), None]
        
        result = dedup_handler.check_duplicate(sample_email_identifiers)
        
        assert result.is_duplicate
        assert DuplicateSource.MESSAGE_ID in result.duplicate_sources
        assert result.first_seen == first_seen
    
    def test_check_duplicate_content_hash_duplicate(self, dedup_handler, sample_email_identifiers, mock_redis, mock_db):
        """Test duplicate detection via content hash."""
        # Mock database to return content hash duplicate
        first_seen = datetime.utcnow() - timedelta(hours=3)
        mock_redis.get.side_effect = [None, None, json.dumps({
            'first_seen': first_seen.isoformat(),
            'count': 3
        })]
        
        result = dedup_handler.check_duplicate(sample_email_identifiers)
        
        assert result.is_duplicate
        assert DuplicateSource.CONTENT_HASH in result.duplicate_sources
        assert result.first_seen == first_seen
        assert result.duplicate_count == 3
    
    def test_check_duplicate_multi_source(self, dedup_handler, sample_email_identifiers, mock_redis, mock_db):
        """Test duplicate detection with multiple sources."""
        # Mock all three sources to return duplicates
        first_seen = datetime.utcnow() - timedelta(hours=1)
        cache_data = {
            'first_seen': first_seen.isoformat(),
            'count': 1
        }
        mock_redis.get.return_value = json.dumps(cache_data)
        
        result = dedup_handler.check_duplicate(sample_email_identifiers)
        
        assert result.is_duplicate
        assert len(result.duplicate_sources) == 3
        assert DuplicateSource.UID in result.duplicate_sources
        assert DuplicateSource.MESSAGE_ID in result.duplicate_sources
        assert DuplicateSource.CONTENT_HASH in result.duplicate_sources
        assert result.confidence_score >= 0.995  # High confidence with multiple sources
    
    def test_check_duplicate_redis_failure(self, dedup_handler, sample_email_identifiers, mock_redis, mock_db):
        """Test duplicate check with Redis failure."""
        # Mock Redis to raise error
        mock_redis.get.side_effect = RedisError("Redis connection failed")
        mock_db.get_connection.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value.fetchone.return_value = None
        
        result = dedup_handler.check_duplicate(sample_email_identifiers)
        
        # Should still work with database fallback
        assert not result.is_duplicate
        assert dedup_handler._redis_healthy is False
    
    def test_check_duplicate_database_failure(self, dedup_handler, sample_email_identifiers, mock_redis, mock_db):
        """Test duplicate check with database failure."""
        # Mock database to raise error
        mock_redis.get.return_value = None
        mock_db.get_connection.side_effect = DatabaseError("Database connection failed")
        
        result = dedup_handler.check_duplicate(sample_email_identifiers)
        
        # Should return safe result (potential duplicate)
        assert result.is_duplicate
        assert result.confidence_score == 0.5  # Low confidence due to error
    
    def test_mark_as_processed(self, dedup_handler, sample_email_identifiers, mock_redis, mock_db):
        """Test marking email as processed."""
        result = dedup_handler.mark_as_processed(sample_email_identifiers)
        
        assert result is True
        # Verify database insert was called
        mock_db.get_connection.assert_called()
    
    def test_get_deduplication_stats(self, dedup_handler, mock_redis):
        """Test getting deduplication statistics."""
        # Set up some stats
        dedup_handler._stats.total_checks = 100
        dedup_handler._stats.duplicates_found = 10
        dedup_handler._stats.uid_duplicates = 5
        dedup_handler._stats.message_id_duplicates = 3
        dedup_handler._stats.content_hash_duplicates = 2
        
        stats = dedup_handler.get_deduplication_stats()
        
        assert stats.total_checks == 100
        assert stats.duplicates_found == 10
        assert stats.duplicate_rate == 10.0
        assert stats.uid_duplicates == 5
        assert stats.message_id_duplicates == 3
        assert stats.content_hash_duplicates == 2
    
    def test_cleanup_expired_entries(self, dedup_handler, mock_db):
        """Test cleanup of expired entries."""
        # Mock database to return cleanup count
        mock_db.get_connection.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value.rowcount = 50
        
        cleaned_count = dedup_handler.cleanup_expired_entries(days_old=30)
        
        assert cleaned_count == 50
        # Verify database delete was called
        mock_db.get_connection.assert_called()
    
    def test_validate_accuracy_perfect_score(self, dedup_handler):
        """Test accuracy validation with perfect score."""
        # Create test emails
        test_emails = []
        for i in range(10):
            test_emails.append(EmailIdentifiers(
                uid=f"test_{i}",
                message_id=f"<test_{i}@example.com>",
                content_hash=calculate_content_hash(f"Test content {i}"),
                account_id="test_account",
                received_date=datetime.utcnow()
            ))
        
        # Mock to simulate perfect deduplication
        with patch.object(dedup_handler, 'check_duplicate') as mock_check:
            # First call returns not duplicate, second call returns duplicate
            mock_check.side_effect = [
                DeduplicationResult(is_duplicate=False, duplicate_sources=[]),
                DeduplicationResult(is_duplicate=True, duplicate_sources=[DuplicateSource.UID])
            ] * len(test_emails)
            
            accuracy_results = dedup_handler.validate_accuracy(test_emails)
            
            assert accuracy_results['accuracy_percent'] == 100.0
            assert accuracy_results['meets_99_99_target'] is True
            assert accuracy_results['false_positives'] == 0
            assert accuracy_results['false_negatives'] == 0
    
    def test_validate_accuracy_with_errors(self, dedup_handler):
        """Test accuracy validation with some errors."""
        test_emails = [EmailIdentifiers(
            uid="test_1",
            message_id="<test_1@example.com>",
            content_hash=calculate_content_hash("Test content"),
            account_id="test_account",
            received_date=datetime.utcnow()
        )]
        
        # Mock to simulate some false positives/negatives
        with patch.object(dedup_handler, 'check_duplicate') as mock_check:
            mock_check.side_effect = [
                DeduplicationResult(is_duplicate=True, duplicate_sources=[DuplicateSource.UID]),  # False positive
                DeduplicationResult(is_duplicate=False, duplicate_sources=[])  # False negative
            ]
            
            accuracy_results = dedup_handler.validate_accuracy(test_emails)
            
            assert accuracy_results['accuracy_percent'] == 0.0
            assert accuracy_results['meets_99_99_target'] is False
            assert accuracy_results['false_positives'] == 1
            assert accuracy_results['false_negatives'] == 1


class TestDeduplicationAccuracyIntegration:
    """Integration tests for deduplication accuracy."""
    
    @pytest.fixture
    def real_redis(self):
        """Create real Redis client for integration tests."""
        try:
            client = redis.Redis(host='localhost', port=6379, db=15, decode_responses=False)
            client.ping()
            # Clean test database
            client.flushdb()
            return client
        except:
            pytest.skip("Redis not available for integration tests")
    
    @pytest.fixture
    def mock_db_for_integration(self):
        """Create mock database for integration tests."""
        mock_db = Mock(spec=DatabaseManager)
        
        # In-memory storage for testing
        storage = {}
        
        def mock_get_connection():
            mock_connection = Mock()
            mock_cursor = Mock()
            
            def mock_execute(query, params=None):
                if "SELECT" in query:
                    # Simulate database lookup
                    if params:
                        key = f"{params[0]}_{params[1] if len(params) > 1 else ''}"
                        if key in storage:
                            mock_cursor.fetchone.return_value = storage[key]
                        else:
                            mock_cursor.fetchone.return_value = None
                elif "INSERT" in query or "ON CONFLICT" in query:
                    # Simulate database insert
                    if params:
                        key = f"{params[0]}_{params[1] if len(params) > 1 else ''}"
                        storage[key] = (params[6], params[8])  # first_seen, count
                elif "DELETE" in query:
                    # Simulate cleanup
                    mock_cursor.rowcount = len(storage)
                    storage.clear()
            
            mock_cursor.execute = mock_execute
            mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connection.commit = Mock()
            return mock_connection
        
        mock_db.get_connection.return_value.__enter__ = mock_get_connection
        return mock_db
    
    def test_high_volume_deduplication_accuracy(self, real_redis, mock_db_for_integration):
        """Test deduplication accuracy with high volume of emails."""
        handler = MultiLayerDeduplicationHandler(real_redis, mock_db_for_integration)
        
        # Generate test emails with known duplicates
        test_emails = []
        duplicate_pairs = []
        
        # Create 1000 unique emails
        for i in range(1000):
            email = EmailIdentifiers(
                uid=f"email_{i}",
                message_id=f"<email_{i}@example.com>",
                content_hash=calculate_content_hash(f"Unique content {i}"),
                account_id="test_account",
                received_date=datetime.utcnow()
            )
            test_emails.append(email)
        
        # Create 100 duplicate emails (10% duplicate rate)
        for i in range(100):
            original_idx = i % 100  # Duplicate first 100 emails
            duplicate_email = EmailIdentifiers(
                uid=f"dup_{i}",  # Different UID
                message_id=test_emails[original_idx].message_id,  # Same Message-ID
                content_hash=test_emails[original_idx].content_hash,  # Same content hash
                account_id="test_account",
                received_date=datetime.utcnow()
            )
            test_emails.append(duplicate_email)
            duplicate_pairs.append((len(test_emails) - 1, original_idx))
        
        # Process all emails
        results = []
        for email in test_emails:
            result = handler.check_duplicate(email)
            results.append(result)
        
        # Analyze results
        true_positives = 0  # Correctly identified duplicates
        false_positives = 0  # Incorrectly identified as duplicates
        true_negatives = 0  # Correctly identified as unique
        false_negatives = 0  # Missed duplicates
        
        for i, result in enumerate(results):
            is_expected_duplicate = any(i == dup_idx for dup_idx, _ in duplicate_pairs)
            
            if result.is_duplicate and is_expected_duplicate:
                true_positives += 1
            elif result.is_duplicate and not is_expected_duplicate:
                false_positives += 1
            elif not result.is_duplicate and not is_expected_duplicate:
                true_negatives += 1
            else:  # not result.is_duplicate and is_expected_duplicate
                false_negatives += 1
        
        # Calculate accuracy metrics
        total = len(results)
        accuracy = ((true_positives + true_negatives) / total) * 100
        precision = (true_positives / (true_positives + false_positives)) * 100 if (true_positives + false_positives) > 0 else 0
        recall = (true_positives / (true_positives + false_negatives)) * 100 if (true_positives + false_negatives) > 0 else 0
        
        # Verify 99.99% accuracy requirement
        assert accuracy >= 99.99, f"Accuracy {accuracy}% below 99.99% requirement"
        assert precision >= 99.0, f"Precision {precision}% too low"
        assert recall >= 99.0, f"Recall {recall}% too low"
        
        # Verify statistics
        stats = handler.get_deduplication_stats()
        assert stats.total_checks == total
        assert stats.duplicates_found == true_positives + false_positives
        assert stats.accuracy_rate >= 99.99
    
    def test_cross_layer_validation_accuracy(self, real_redis, mock_db_for_integration):
        """Test cross-layer validation accuracy."""
        handler = MultiLayerDeduplicationHandler(real_redis, mock_db_for_integration)
        
        # Test different duplicate scenarios
        base_email = EmailIdentifiers(
            uid="base_email",
            message_id="<base@example.com>",
            content_hash=calculate_content_hash("Base email content"),
            account_id="test_account",
            received_date=datetime.utcnow()
        )
        
        # Process base email first
        result1 = handler.check_duplicate(base_email)
        assert not result1.is_duplicate
        
        # Test UID duplicate
        uid_duplicate = EmailIdentifiers(
            uid="base_email",  # Same UID
            message_id="<different@example.com>",
            content_hash=calculate_content_hash("Different content"),
            account_id="test_account",
            received_date=datetime.utcnow()
        )
        
        result2 = handler.check_duplicate(uid_duplicate)
        assert result2.is_duplicate
        assert DuplicateSource.UID in result2.duplicate_sources
        assert result2.confidence_score >= 0.95
        
        # Test Message-ID duplicate
        msgid_duplicate = EmailIdentifiers(
            uid="different_uid",
            message_id="<base@example.com>",  # Same Message-ID
            content_hash=calculate_content_hash("Different content again"),
            account_id="test_account",
            received_date=datetime.utcnow()
        )
        
        result3 = handler.check_duplicate(msgid_duplicate)
        assert result3.is_duplicate
        assert DuplicateSource.MESSAGE_ID in result3.duplicate_sources
        assert result3.confidence_score >= 0.95
        
        # Test content hash duplicate
        content_duplicate = EmailIdentifiers(
            uid="another_uid",
            message_id="<another@example.com>",
            content_hash=calculate_content_hash("Base email content"),  # Same content
            account_id="test_account",
            received_date=datetime.utcnow()
        )
        
        result4 = handler.check_duplicate(content_duplicate)
        assert result4.is_duplicate
        assert DuplicateSource.CONTENT_HASH in result4.duplicate_sources
        assert result4.confidence_score >= 0.95
        
        # Test multi-source duplicate (highest confidence)
        multi_duplicate = EmailIdentifiers(
            uid="base_email",  # Same UID
            message_id="<base@example.com>",  # Same Message-ID
            content_hash=calculate_content_hash("Base email content"),  # Same content
            account_id="test_account",
            received_date=datetime.utcnow()
        )
        
        result5 = handler.check_duplicate(multi_duplicate)
        assert result5.is_duplicate
        assert len(result5.duplicate_sources) == 3
        assert result5.confidence_score >= 0.99  # Highest confidence
        
        # Verify overall accuracy
        stats = handler.get_deduplication_stats()
        assert stats.accuracy_rate >= 99.99


if __name__ == "__main__":
    pytest.main([__file__, "-v"])