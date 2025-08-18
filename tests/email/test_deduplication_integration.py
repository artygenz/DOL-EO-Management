"""
Integration tests for Multi-Layer Deduplication System with existing components.

Tests integration with UID tracker and other email processing components.
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock

from src.email.deduplication_handler import (
    MultiLayerDeduplicationHandler,
    EmailIdentifiers,
    calculate_content_hash,
    create_email_identifiers
)
from src.email.uid_tracker import UIDTracker, TrackingResult, TrackingStatus
from src.database.models import EmailMetadata


class TestDeduplicationIntegration:
    """Integration tests for deduplication system."""
    
    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        mock_redis = Mock()
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
        mock_db = Mock()
        
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
        """Create deduplication handler."""
        return MultiLayerDeduplicationHandler(mock_redis, mock_db)
    
    @pytest.fixture
    def uid_tracker(self, mock_redis, mock_db):
        """Create UID tracker."""
        return UIDTracker(mock_redis, mock_db)
    
    def test_deduplication_with_uid_tracker_integration(self, dedup_handler, uid_tracker):
        """Test deduplication system integration with UID tracker."""
        # Create test email
        email_content = "This is a test email for integration testing"
        email_identifiers = create_email_identifiers(
            uid="test_email_001",
            message_id="<test_001@example.com>",
            content=email_content,
            account_id="test_account",
            received_date=datetime.utcnow(),
            sender="sender@example.com",
            subject="Test Email"
        )
        
        # Create email metadata
        metadata = EmailMetadata(
            uid=email_identifiers.uid,
            message_id=email_identifiers.message_id,
            sender=email_identifiers.sender,
            subject=email_identifiers.subject,
            received_date=email_identifiers.received_date,
            account_id=email_identifiers.account_id,
            content_hash=email_identifiers.content_hash
        )
        
        # First check - should not be duplicate
        dedup_result = dedup_handler.check_duplicate(email_identifiers)
        assert not dedup_result.is_duplicate
        assert dedup_result.confidence_score == 0.9999
        
        # Track with UID tracker
        tracking_result = uid_tracker.track_email(email_identifiers, metadata)
        assert tracking_result.status == TrackingStatus.NEW
        assert not tracking_result.is_duplicate
        
        # Second check - should be duplicate
        dedup_result2 = dedup_handler.check_duplicate(email_identifiers)
        assert dedup_result2.is_duplicate
        assert len(dedup_result2.duplicate_sources) >= 1
        assert dedup_result2.confidence_score >= 0.95
    
    def test_cross_system_duplicate_detection(self, dedup_handler, uid_tracker):
        """Test duplicate detection across both systems."""
        base_content = "Base email content for cross-system testing"
        
        # Create original email
        original_email = create_email_identifiers(
            uid="original_001",
            message_id="<original@example.com>",
            content=base_content,
            account_id="test_account",
            received_date=datetime.utcnow()
        )
        
        # Process original email
        dedup_result1 = dedup_handler.check_duplicate(original_email)
        assert not dedup_result1.is_duplicate
        
        # Create duplicate with same UID
        uid_duplicate = EmailIdentifiers(
            uid="original_001",  # Same UID
            message_id="<different@example.com>",
            content_hash=calculate_content_hash("Different content"),
            account_id="test_account",
            received_date=datetime.utcnow()
        )
        
        # Should detect UID duplicate
        dedup_result2 = dedup_handler.check_duplicate(uid_duplicate)
        assert dedup_result2.is_duplicate
        
        # Create duplicate with same Message-ID
        msgid_duplicate = EmailIdentifiers(
            uid="different_uid",
            message_id="<original@example.com>",  # Same Message-ID
            content_hash=calculate_content_hash("Different content again"),
            account_id="test_account",
            received_date=datetime.utcnow()
        )
        
        # Should detect Message-ID duplicate
        dedup_result3 = dedup_handler.check_duplicate(msgid_duplicate)
        assert dedup_result3.is_duplicate
        
        # Create duplicate with same content
        content_duplicate = EmailIdentifiers(
            uid="another_uid",
            message_id="<another@example.com>",
            content_hash=calculate_content_hash(base_content),  # Same content
            account_id="test_account",
            received_date=datetime.utcnow()
        )
        
        # Should detect content duplicate
        dedup_result4 = dedup_handler.check_duplicate(content_duplicate)
        assert dedup_result4.is_duplicate
    
    def test_performance_with_high_volume(self, dedup_handler):
        """Test deduplication performance with high volume of emails."""
        emails = []
        processing_times = []
        
        # Generate 1000 test emails
        for i in range(1000):
            email = create_email_identifiers(
                uid=f"perf_test_{i:04d}",
                message_id=f"<perf_{i:04d}@example.com>",
                content=f"Performance test email content {i}",
                account_id="perf_test_account",
                received_date=datetime.utcnow()
            )
            emails.append(email)
        
        # Process all emails and measure performance
        start_time = time.time()
        
        for email in emails:
            email_start = time.time()
            result = dedup_handler.check_duplicate(email)
            processing_time = (time.time() - email_start) * 1000
            processing_times.append(processing_time)
            
            # First occurrence should not be duplicate
            assert not result.is_duplicate
        
        total_time = time.time() - start_time
        
        # Performance assertions
        avg_processing_time = sum(processing_times) / len(processing_times)
        throughput = len(emails) / total_time
        
        assert avg_processing_time < 1.0  # Less than 1ms per email
        assert throughput > 1000  # More than 1000 emails per second
        
        # Test duplicate detection on second pass
        duplicate_count = 0
        for email in emails[:100]:  # Test first 100 emails
            result = dedup_handler.check_duplicate(email)
            if result.is_duplicate:
                duplicate_count += 1
        
        # Should detect all as duplicates
        assert duplicate_count == 100
    
    def test_accuracy_validation_comprehensive(self, dedup_handler):
        """Comprehensive accuracy validation test."""
        test_scenarios = []
        
        # Create base emails
        for i in range(100):
            base_email = create_email_identifiers(
                uid=f"accuracy_test_{i:03d}",
                message_id=f"<accuracy_{i:03d}@example.com>",
                content=f"Accuracy test email content {i}",
                account_id="accuracy_test",
                received_date=datetime.utcnow()
            )
            test_scenarios.append(("original", base_email))
        
        # Create known duplicates
        for i in range(20):
            # UID duplicates
            uid_dup = EmailIdentifiers(
                uid=f"accuracy_test_{i:03d}",  # Same UID as original
                message_id=f"<uid_dup_{i}@example.com>",
                content_hash=calculate_content_hash(f"Different content {i}"),
                account_id="accuracy_test",
                received_date=datetime.utcnow()
            )
            test_scenarios.append(("uid_duplicate", uid_dup))
            
            # Message-ID duplicates
            msgid_dup = EmailIdentifiers(
                uid=f"msgid_dup_{i}",
                message_id=f"<accuracy_{i:03d}@example.com>",  # Same Message-ID
                content_hash=calculate_content_hash(f"Different content {i}"),
                account_id="accuracy_test",
                received_date=datetime.utcnow()
            )
            test_scenarios.append(("msgid_duplicate", msgid_dup))
            
            # Content duplicates
            content_dup = EmailIdentifiers(
                uid=f"content_dup_{i}",
                message_id=f"<content_dup_{i}@example.com>",
                content_hash=calculate_content_hash(f"Accuracy test email content {i}"),  # Same content
                account_id="accuracy_test",
                received_date=datetime.utcnow()
            )
            test_scenarios.append(("content_duplicate", content_dup))
        
        # Process all scenarios
        results = []
        for scenario_type, email in test_scenarios:
            result = dedup_handler.check_duplicate(email)
            results.append((scenario_type, result))
        
        # Analyze results
        correct_predictions = 0
        total_predictions = len(results)
        
        for i, (scenario_type, result) in enumerate(results):
            if scenario_type == "original":
                # First occurrence should not be duplicate
                if not result.is_duplicate:
                    correct_predictions += 1
            else:
                # Duplicates should be detected
                if result.is_duplicate:
                    correct_predictions += 1
        
        accuracy = (correct_predictions / total_predictions) * 100
        
        # Verify 99.99% accuracy requirement
        assert accuracy >= 99.99, f"Accuracy {accuracy}% below 99.99% requirement"
        
        # Verify system statistics
        stats = dedup_handler.get_deduplication_stats()
        assert stats.total_checks == total_predictions
        assert stats.accuracy_rate >= 99.99


if __name__ == "__main__":
    pytest.main([__file__, "-v"])