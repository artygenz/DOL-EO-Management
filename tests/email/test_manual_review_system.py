"""
Comprehensive tests for the Confidence-Based Manual Review System

Tests confidence threshold enforcement, manual review queue management,
classification error detection, and human-in-the-loop validation workflow.
"""

import pytest
import tempfile
import shutil
import sqlite3
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from pathlib import Path

from src.email.manual_review_system import (
    ManualReviewSystem, ManualReviewQueue, HumanInTheLoopValidator,
    ManualReviewItem, ClassificationError, RetrainingTrigger,
    ReviewStatus, ReviewPriority, ErrorType
)
from src.email.email_classifier import EmailType, ClassificationResult, EmailFeatures
from src.email.content_extractor import ExtractedContent, EmailHeaders, ThreadAnalysis
from src.email.security_validator import SecurityValidationResult


class TestManualReviewQueue:
    """Test suite for ManualReviewQueue"""
    
    @pytest.fixture
    def review_queue(self):
        """Create review queue for testing"""
        return ManualReviewQueue(max_size=100)
    
    @pytest.fixture
    def sample_review_item(self):
        """Create sample review item"""
        return ManualReviewItem(
            review_id="test-review-123",
            email_uid="email-123",
            message_id="<test@example.com>",
            extracted_content=Mock(),
            security_result=Mock(),
            classification_result=Mock(),
            review_status=ReviewStatus.PENDING,
            review_priority=ReviewPriority.MEDIUM,
            created_timestamp=datetime.utcnow()
        )
    
    def test_add_item_success(self, review_queue, sample_review_item):
        """Test successful addition of review item"""
        result = review_queue.add_item(sample_review_item)
        
        assert result is True
        assert review_queue.get_queue_size() == 1
    
    def test_get_next_item_priority_order(self, review_queue):
        """Test that items are retrieved in priority order"""
        # Add items with different priorities
        high_priority_item = ManualReviewItem(
            review_id="high-priority",
            email_uid="email-1",
            message_id="<high@example.com>",
            extracted_content=Mock(),
            security_result=Mock(),
            classification_result=Mock(),
            review_status=ReviewStatus.PENDING,
            review_priority=ReviewPriority.HIGH,
            created_timestamp=datetime.utcnow()
        )
        
        low_priority_item = ManualReviewItem(
            review_id="low-priority",
            email_uid="email-2",
            message_id="<low@example.com>",
            extracted_content=Mock(),
            security_result=Mock(),
            classification_result=Mock(),
            review_status=ReviewStatus.PENDING,
            review_priority=ReviewPriority.LOW,
            created_timestamp=datetime.utcnow()
        )
        
        # Add low priority first, then high priority
        review_queue.add_item(low_priority_item)
        review_queue.add_item(high_priority_item)
        
        # High priority should come out first
        next_item = review_queue.get_next_item()
        assert next_item is not None
        assert next_item.review_priority == ReviewPriority.HIGH
        
        # Low priority should come out second
        next_item = review_queue.get_next_item()
        assert next_item is not None
        assert next_item.review_priority == ReviewPriority.LOW
    
    def test_get_priority_counts(self, review_queue):
        """Test priority count tracking"""
        # Add items with different priorities
        for priority in [ReviewPriority.HIGH, ReviewPriority.MEDIUM, ReviewPriority.LOW]:
            item = ManualReviewItem(
                review_id=f"item-{priority.value}",
                email_uid=f"email-{priority.value}",
                message_id=f"<{priority.value}@example.com>",
                extracted_content=Mock(),
                security_result=Mock(),
                classification_result=Mock(),
                review_status=ReviewStatus.PENDING,
                review_priority=priority,
                created_timestamp=datetime.utcnow()
            )
            review_queue.add_item(item)
        
        counts = review_queue.get_priority_counts()
        assert counts[ReviewPriority.HIGH] == 1
        assert counts[ReviewPriority.MEDIUM] == 1
        assert counts[ReviewPriority.LOW] == 1
        assert counts[ReviewPriority.CRITICAL] == 0
    
    def test_empty_queue_timeout(self, review_queue):
        """Test timeout behavior on empty queue"""
        next_item = review_queue.get_next_item(timeout=0.1)
        assert next_item is None


class TestManualReviewSystem:
    """Test suite for ManualReviewSystem"""
    
    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database path"""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_file.close()
        yield temp_file.name
        Path(temp_file.name).unlink(missing_ok=True)
    
    @pytest.fixture
    def review_system(self, temp_db_path):
        """Create review system for testing"""
        return ManualReviewSystem(database_path=temp_db_path, enable_auto_retraining=True)
    
    @pytest.fixture
    def sample_extracted_content(self):
        """Create sample extracted content"""
        headers = EmailHeaders(
            message_id="<test@example.com>",
            sender="test.user@dol.gov",
            sender_name="Test User",
            recipients=["recipient@dol.gov"],
            cc_recipients=[],
            bcc_recipients=[],
            subject="Test Email Subject",
            date=datetime.now(),
            reply_to=None,
            in_reply_to=None,
            references=[],
            thread_topic=None,
            priority=None,
            content_type="text/plain",
            encoding="utf-8",
            custom_headers={}
        )
        
        thread_analysis = ThreadAnalysis(
            thread_id="thread-123",
            is_reply=False,
            is_forward=False,
            parent_message_id=None,
            thread_depth=0,
            conversation_participants={"test.user@dol.gov"},
            thread_subject="Test Email Subject",
            original_subject="Test Email Subject",
            reply_chain_length=0
        )
        
        return ExtractedContent(
            headers=headers,
            plain_text="This is a test email content",
            html_content="<p>This is a test email content</p>",
            sanitized_html="<p>This is a test email content</p>",
            attachments=[],
            thread_analysis=thread_analysis,
            content_hash="test-hash-123",
            extraction_metadata={},
            security_flags=[]
        )
    
    @pytest.fixture
    def sample_security_result(self):
        """Create sample security validation result"""
        return SecurityValidationResult(
            is_valid=True,
            sender_authorized=True,
            content_safe=True,
            attachments_safe=True,
            digital_signature_valid=True,
            threat_level="LOW",
            security_issues=[],
            quarantine_required=False,
            validation_timestamp=datetime.now()
        )
    
    @pytest.fixture
    def sample_classification_result(self):
        """Create sample classification result"""
        return ClassificationResult(
            email_type=EmailType.DEVELOPER_UPDATE,
            confidence_score=0.75,  # Below threshold
            feature_importance={'technical_terms': 0.5, 'sender_role': 0.3},
            classification_metadata={'model_version': 'v1.0.0'},
            requires_manual_review=True,
            alternative_classifications=[(EmailType.PMO_RESPONSE, 0.65)],
            classification_timestamp=datetime.utcnow()
        )
    
    def test_confidence_threshold_enforcement_below_threshold(self, review_system, 
                                                            sample_classification_result,
                                                            sample_extracted_content,
                                                            sample_security_result):
        """Test that low confidence classifications require manual review"""
        # Set confidence below threshold
        sample_classification_result.confidence_score = 0.70
        
        result = review_system.evaluate_classification_confidence(
            sample_classification_result, sample_extracted_content, sample_security_result
        )
        
        assert result is False  # Should require manual review
    
    def test_confidence_threshold_enforcement_above_threshold(self, review_system,
                                                            sample_classification_result,
                                                            sample_extracted_content,
                                                            sample_security_result):
        """Test that high confidence classifications can be processed automatically"""
        # Set confidence above threshold
        sample_classification_result.confidence_score = 0.90
        sample_classification_result.alternative_classifications = []  # No ambiguity
        
        result = review_system.evaluate_classification_confidence(
            sample_classification_result, sample_extracted_content, sample_security_result
        )
        
        assert result is True  # Should allow automated processing
    
    def test_ambiguous_classification_detection(self, review_system,
                                              sample_classification_result,
                                              sample_extracted_content,
                                              sample_security_result):
        """Test detection of ambiguous classifications"""
        # Set up ambiguous classification (close alternatives)
        sample_classification_result.confidence_score = 0.85
        sample_classification_result.alternative_classifications = [
            (EmailType.PMO_RESPONSE, 0.80)  # Very close to main classification
        ]
        
        result = review_system.evaluate_classification_confidence(
            sample_classification_result, sample_extracted_content, sample_security_result
        )
        
        assert result is False  # Should require manual review due to ambiguity
    
    def test_security_review_requirement(self, review_system,
                                       sample_classification_result,
                                       sample_extracted_content,
                                       sample_security_result):
        """Test that security issues trigger manual review"""
        # Set high confidence but security issues
        sample_classification_result.confidence_score = 0.90
        sample_security_result.sender_authorized = False
        
        result = review_system.evaluate_classification_confidence(
            sample_classification_result, sample_extracted_content, sample_security_result
        )
        
        assert result is False  # Should require manual review due to security
    
    def test_create_manual_review(self, review_system,
                                sample_classification_result,
                                sample_extracted_content,
                                sample_security_result):
        """Test creation of manual review item"""
        review_id = review_system.create_manual_review(
            sample_classification_result,
            sample_extracted_content,
            sample_security_result,
            ReviewPriority.HIGH,
            "Low confidence classification"
        )
        
        assert review_id != ""
        assert review_system.review_stats['total_reviews_created'] == 1
        assert review_system.review_queue.get_queue_size() == 1
    
    def test_get_next_review_item(self, review_system,
                                sample_classification_result,
                                sample_extracted_content,
                                sample_security_result):
        """Test retrieval of next review item"""
        # Create review item
        review_id = review_system.create_manual_review(
            sample_classification_result,
            sample_extracted_content,
            sample_security_result
        )
        
        # Get next item
        review_item = review_system.get_next_review_item()
        
        assert review_item is not None
        assert review_item.review_id == review_id
        assert review_item.review_status == ReviewStatus.IN_REVIEW
    
    def test_complete_manual_review_approved(self, review_system,
                                           sample_classification_result,
                                           sample_extracted_content,
                                           sample_security_result):
        """Test completion of manual review with approval"""
        # Create and get review item
        review_id = review_system.create_manual_review(
            sample_classification_result,
            sample_extracted_content,
            sample_security_result
        )
        
        # Complete review with same classification (approval)
        result = review_system.complete_manual_review(
            review_id,
            EmailType.DEVELOPER_UPDATE,  # Same as original
            0.95,
            "Looks correct",
            "reviewer-123"
        )
        
        assert result is True
        assert review_system.review_stats['total_reviews_completed'] == 1
        assert review_system.review_stats['total_reviews_approved'] == 1
    
    def test_complete_manual_review_rejected(self, review_system,
                                           sample_classification_result,
                                           sample_extracted_content,
                                           sample_security_result):
        """Test completion of manual review with rejection"""
        # Create and get review item
        review_id = review_system.create_manual_review(
            sample_classification_result,
            sample_extracted_content,
            sample_security_result
        )
        
        # Complete review with different classification (rejection)
        result = review_system.complete_manual_review(
            review_id,
            EmailType.PMO_RESPONSE,  # Different from original
            0.90,
            "Should be PMO response",
            "reviewer-123"
        )
        
        assert result is True
        assert review_system.review_stats['total_reviews_completed'] == 1
        assert review_system.review_stats['total_reviews_rejected'] == 1
        assert review_system.review_stats['total_errors_detected'] == 1
    
    def test_classification_error_detection(self, review_system):
        """Test detection of classification errors"""
        # Create some classification errors in database
        with sqlite3.connect(review_system.database_path) as conn:
            cursor = conn.cursor()
            
            # Insert test errors
            test_errors = [
                ("error-1", "email-1", "<msg1@example.com>", "DEVELOPER_UPDATE", 
                 "PMO_RESPONSE", 0.75, "WRONG_CLASSIFICATION", 
                 datetime.utcnow().isoformat(), "{}", "", "v1.0.0", 0),
                ("error-2", "email-2", "<msg2@example.com>", "NEW_EO", 
                 "EXECUTIVE_REQUEST", 0.65, "WRONG_CLASSIFICATION", 
                 datetime.utcnow().isoformat(), "{}", "", "v1.0.0", 0)
            ]
            
            cursor.executemany("""
                INSERT INTO classification_errors VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, test_errors)
            conn.commit()
        
        # Detect errors
        errors = review_system.detect_classification_errors(24)
        
        assert len(errors) == 2
        assert all(error.error_type == ErrorType.WRONG_CLASSIFICATION for error in errors)
    
    def test_retraining_trigger_error_count(self, review_system):
        """Test retraining trigger based on error count"""
        # Create enough errors to trigger retraining
        with sqlite3.connect(review_system.database_path) as conn:
            cursor = conn.cursor()
            
            # Insert multiple errors
            test_errors = []
            for i in range(15):  # Above threshold of 10
                test_errors.append((
                    f"error-{i}", f"email-{i}", f"<msg{i}@example.com>",
                    "DEVELOPER_UPDATE", "PMO_RESPONSE", 0.75, "WRONG_CLASSIFICATION",
                    datetime.utcnow().isoformat(), "{}", "", "v1.0.0", 0
                ))
            
            cursor.executemany("""
                INSERT INTO classification_errors VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, test_errors)
            conn.commit()
        
        # Check retraining triggers
        should_retrain = review_system.check_retraining_triggers()
        
        assert should_retrain is True
        assert review_system.review_stats['total_retraining_triggered'] == 1
    
    def test_review_statistics(self, review_system,
                             sample_classification_result,
                             sample_extracted_content,
                             sample_security_result):
        """Test comprehensive review statistics"""
        # Create some review activity
        review_id = review_system.create_manual_review(
            sample_classification_result,
            sample_extracted_content,
            sample_security_result,
            ReviewPriority.HIGH
        )
        
        review_system.complete_manual_review(
            review_id,
            EmailType.PMO_RESPONSE,
            0.90,
            "Corrected classification"
        )
        
        # Get statistics
        stats = review_system.get_review_statistics()
        
        assert stats['total_reviews_created'] == 1
        assert stats['total_reviews_completed'] == 1
        assert stats['total_reviews_rejected'] == 1
        assert stats['total_errors_detected'] == 1
        assert 'priority_breakdown' in stats
        assert 'recent_errors_24h' in stats
    
    def test_database_persistence(self, review_system,
                                sample_classification_result,
                                sample_extracted_content,
                                sample_security_result):
        """Test that review items are persisted to database"""
        # Create review item
        review_id = review_system.create_manual_review(
            sample_classification_result,
            sample_extracted_content,
            sample_security_result
        )
        
        # Verify in database
        with sqlite3.connect(review_system.database_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM review_items WHERE review_id = ?", (review_id,))
            count = cursor.fetchone()[0]
            
        assert count == 1


class TestHumanInTheLoopValidator:
    """Test suite for HumanInTheLoopValidator"""
    
    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database path"""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_file.close()
        yield temp_file.name
        Path(temp_file.name).unlink(missing_ok=True)
    
    @pytest.fixture
    def review_system(self, temp_db_path):
        """Create review system for testing"""
        return ManualReviewSystem(database_path=temp_db_path)
    
    @pytest.fixture
    def validator(self, review_system):
        """Create validator for testing"""
        return HumanInTheLoopValidator(review_system)
    
    @pytest.fixture
    def sample_review_item(self):
        """Create sample review item"""
        headers = EmailHeaders(
            message_id="<test@example.com>",
            sender="test.user@dol.gov",
            sender_name="Test User",
            recipients=["recipient@dol.gov"],
            cc_recipients=[],
            bcc_recipients=[],
            subject="Test Email Subject",
            date=datetime.now(),
            reply_to=None,
            in_reply_to=None,
            references=[],
            thread_topic=None,
            priority=None,
            content_type="text/plain",
            encoding="utf-8",
            custom_headers={}
        )
        
        extracted_content = ExtractedContent(
            headers=headers,
            plain_text="This is a test email content",
            html_content="<p>This is a test email content</p>",
            sanitized_html="<p>This is a test email content</p>",
            attachments=[],
            thread_analysis=Mock(),
            content_hash="test-hash-456",
            extraction_metadata={},
            security_flags=[]
        )
        
        security_result = SecurityValidationResult(
            is_valid=True,
            sender_authorized=True,
            content_safe=True,
            attachments_safe=True,
            digital_signature_valid=True,
            threat_level="LOW",
            security_issues=[],
            quarantine_required=False,
            validation_timestamp=datetime.now()
        )
        
        classification_result = ClassificationResult(
            email_type=EmailType.DEVELOPER_UPDATE,
            confidence_score=0.75,
            feature_importance={'technical_terms': 0.5},
            classification_metadata={'model_version': 'v1.0.0'},
            requires_manual_review=True,
            alternative_classifications=[(EmailType.PMO_RESPONSE, 0.65)],
            classification_timestamp=datetime.utcnow()
        )
        
        return ManualReviewItem(
            review_id="test-review-123",
            email_uid="email-123",
            message_id="<test@example.com>",
            extracted_content=extracted_content,
            security_result=security_result,
            classification_result=classification_result,
            review_status=ReviewStatus.PENDING,
            review_priority=ReviewPriority.MEDIUM,
            created_timestamp=datetime.utcnow()
        )
    
    def test_start_review_session(self, validator, review_system, sample_review_item):
        """Test starting a review session"""
        # Add item to queue
        review_system.review_queue.add_item(sample_review_item)
        
        # Start review session
        review_item = validator.start_review_session("reviewer-123")
        
        assert review_item is not None
        assert review_item.assigned_reviewer == "reviewer-123"
        assert review_item.review_id in validator.active_reviews
    
    def test_submit_review_decision(self, validator, review_system, sample_review_item):
        """Test submitting review decision"""
        # Add item to queue and start session
        review_system.review_queue.add_item(sample_review_item)
        review_item = validator.start_review_session("reviewer-123")
        
        # Submit decision
        result = validator.submit_review_decision(
            review_item.review_id,
            EmailType.PMO_RESPONSE,
            0.90,
            "Should be PMO response"
        )
        
        assert result is True
        assert review_item.review_id not in validator.active_reviews
    
    def test_get_review_context(self, validator, review_system, sample_review_item):
        """Test getting review context"""
        # Add item to queue and start session
        review_system.review_queue.add_item(sample_review_item)
        review_item = validator.start_review_session("reviewer-123")
        
        # Get context
        context = validator.get_review_context(review_item.review_id)
        
        assert context is not None
        assert context['review_id'] == review_item.review_id
        assert context['email_subject'] == "Test Email Subject"
        assert context['email_sender'] == "test.user@dol.gov"
        assert context['original_classification'] == "DEVELOPER_UPDATE"
        assert context['confidence_score'] == 0.75
        assert 'alternative_classifications' in context
        assert 'security_status' in context
    
    def test_empty_queue_session(self, validator):
        """Test starting session with empty queue"""
        review_item = validator.start_review_session("reviewer-123")
        assert review_item is None
    
    def test_invalid_review_decision(self, validator):
        """Test submitting decision for invalid review"""
        result = validator.submit_review_decision(
            "invalid-review-id",
            EmailType.PMO_RESPONSE,
            0.90,
            "Test notes"
        )
        
        assert result is False


class TestConfidenceThresholdEnforcement:
    """Test suite for confidence threshold enforcement scenarios"""
    
    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database path"""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_file.close()
        yield temp_file.name
        Path(temp_file.name).unlink(missing_ok=True)
    
    @pytest.fixture
    def review_system(self, temp_db_path):
        """Create review system for testing"""
        return ManualReviewSystem(database_path=temp_db_path)
    
    def test_confidence_exactly_at_threshold(self, review_system):
        """Test behavior when confidence is exactly at threshold"""
        classification_result = Mock()
        classification_result.confidence_score = 0.80  # Exactly at threshold
        classification_result.alternative_classifications = []
        
        extracted_content = Mock()
        extracted_content.headers.sender = "normal.user@dol.gov"
        extracted_content.headers.subject = "Regular email"
        extracted_content.plain_text = "Normal content"
        
        security_result = Mock()
        security_result.sender_authorized = True
        security_result.content_safe = True
        security_result.attachments_safe = True
        security_result.threat_level = "LOW"
        
        result = review_system.evaluate_classification_confidence(
            classification_result, extracted_content, security_result
        )
        
        assert result is True  # Should pass at exactly threshold
    
    def test_executive_sender_requires_review(self, review_system):
        """Test that executive senders always require review"""
        classification_result = Mock()
        classification_result.confidence_score = 0.95  # High confidence
        classification_result.alternative_classifications = []
        
        extracted_content = Mock()
        extracted_content.headers.sender = "secretary@dol.gov"  # Executive sender
        extracted_content.headers.subject = "Regular email"
        extracted_content.plain_text = "Normal content"
        
        security_result = Mock()
        security_result.sender_authorized = True
        security_result.content_safe = True
        security_result.attachments_safe = True
        security_result.threat_level = "LOW"
        
        result = review_system.evaluate_classification_confidence(
            classification_result, extracted_content, security_result
        )
        
        assert result is False  # Should require review despite high confidence
    
    def test_urgent_content_requires_review(self, review_system):
        """Test that urgent content requires review"""
        classification_result = Mock()
        classification_result.confidence_score = 0.90  # High confidence
        classification_result.alternative_classifications = []
        
        extracted_content = Mock()
        extracted_content.headers.sender = "normal.user@dol.gov"
        extracted_content.headers.subject = "URGENT: Critical issue"  # Urgent content
        extracted_content.plain_text = "This is an emergency situation"
        
        security_result = Mock()
        security_result.sender_authorized = True
        security_result.content_safe = True
        security_result.attachments_safe = True
        security_result.threat_level = "LOW"
        
        result = review_system.evaluate_classification_confidence(
            classification_result, extracted_content, security_result
        )
        
        assert result is False  # Should require review due to urgent content
    
    def test_medium_threat_level_requires_review(self, review_system):
        """Test that medium threat level requires review"""
        classification_result = Mock()
        classification_result.confidence_score = 0.90  # High confidence
        classification_result.alternative_classifications = []
        
        extracted_content = Mock()
        extracted_content.headers.sender = "normal.user@dol.gov"
        extracted_content.headers.subject = "Regular email"
        extracted_content.plain_text = "Normal content"
        
        security_result = Mock()
        security_result.sender_authorized = True
        security_result.content_safe = True
        security_result.attachments_safe = True
        security_result.threat_level = "MEDIUM"  # Medium threat
        
        result = review_system.evaluate_classification_confidence(
            classification_result, extracted_content, security_result
        )
        
        assert result is False  # Should require review due to security threat


if __name__ == "__main__":
    pytest.main([__file__])