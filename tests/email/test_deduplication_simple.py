"""
Simple focused tests for Multi-Layer Deduplication System core functionality.
"""

import pytest
from datetime import datetime
from src.email.deduplication_handler import (
    EmailIdentifiers,
    DeduplicationResult,
    DuplicateSource,
    calculate_content_hash,
    create_email_identifiers
)


class TestDeduplicationCore:
    """Test core deduplication functionality."""
    
    def test_email_identifiers_creation(self):
        """Test creating email identifiers."""
        uid = "test_001"
        message_id = "<test@example.com>"
        content = "Test email content"
        account_id = "test_account"
        received_date = datetime.utcnow()
        
        identifiers = create_email_identifiers(
            uid, message_id, content, account_id, received_date
        )
        
        assert identifiers.uid == uid
        assert identifiers.message_id == message_id
        assert identifiers.account_id == account_id
        assert identifiers.received_date == received_date
        assert len(identifiers.content_hash) == 64  # SHA-256 length
    
    def test_content_hash_consistency(self):
        """Test that content hash is consistent."""
        content1 = "This is test content"
        content2 = "This is test content"
        content3 = "This is different content"
        
        hash1 = calculate_content_hash(content1)
        hash2 = calculate_content_hash(content2)
        hash3 = calculate_content_hash(content3)
        
        assert hash1 == hash2  # Same content should have same hash
        assert hash1 != hash3  # Different content should have different hash
        assert len(hash1) == 64  # SHA-256 hex length
    
    def test_content_hash_normalization(self):
        """Test content normalization in hash calculation."""
        content1 = "This  is   test\n\n  content"
        content2 = "This is test content"
        
        hash1 = calculate_content_hash(content1, normalize=True)
        hash2 = calculate_content_hash(content2, normalize=True)
        
        assert hash1 == hash2  # Should be same after normalization
    
    def test_deduplication_result_confidence_scoring(self):
        """Test confidence scoring in deduplication results."""
        # Non-duplicate should have 99.99% confidence
        result1 = DeduplicationResult(
            is_duplicate=False,
            duplicate_sources=[]
        )
        assert result1.confidence_score == 0.9999
        
        # Single source duplicate
        result2 = DeduplicationResult(
            is_duplicate=True,
            duplicate_sources=[DuplicateSource.UID]
        )
        assert result2.confidence_score == 0.965  # 95% + 1.5%
        
        # Multi-source duplicate (highest confidence)
        result3 = DeduplicationResult(
            is_duplicate=True,
            duplicate_sources=[
                DuplicateSource.UID,
                DuplicateSource.MESSAGE_ID,
                DuplicateSource.CONTENT_HASH
            ]
        )
        assert result3.confidence_score == 0.995  # 95% + 3*1.5%
    
    def test_email_identifiers_validation(self):
        """Test email identifiers validation."""
        received_date = datetime.utcnow()
        valid_hash = "a" * 64
        
        # Valid identifiers should work
        identifiers = EmailIdentifiers(
            uid="test_001",
            message_id="<test@example.com>",
            content_hash=valid_hash,
            account_id="test_account",
            received_date=received_date
        )
        assert identifiers.uid == "test_001"
        
        # Empty UID should raise error
        with pytest.raises(ValueError, match="Email UID cannot be empty"):
            EmailIdentifiers(
                uid="",
                message_id="<test@example.com>",
                content_hash=valid_hash,
                account_id="test_account",
                received_date=received_date
            )
        
        # Invalid content hash should raise error
        with pytest.raises(ValueError, match="Content hash must be SHA-256"):
            EmailIdentifiers(
                uid="test_001",
                message_id="<test@example.com>",
                content_hash="invalid",
                account_id="test_account",
                received_date=received_date
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])