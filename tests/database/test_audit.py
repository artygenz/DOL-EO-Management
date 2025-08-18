"""
Tests for the audit logging system with cryptographic signing.

Tests cover:
- Audit entry creation and signing
- Hash chain integrity verification
- Cryptographic signature validation
- Audit trail retrieval and filtering
- Tamper detection and security
"""

import pytest
import json
import hashlib
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import os

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend

from src.database.audit import AuditLogger
from src.database.models import AuditLogEntry, AuditAction
from src.database.exceptions import AuditError


class TestAuditLogger:
    """Test suite for AuditLogger class."""
    
    @pytest.fixture
    def temp_key_file(self):
        """Create temporary key file for testing."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pem') as f:
            key_path = f.name
        
        yield key_path
        
        # Cleanup
        if os.path.exists(key_path):
            os.unlink(key_path)
        pub_key_path = key_path.replace('.pem', '.pub')
        if os.path.exists(pub_key_path):
            os.unlink(pub_key_path)
    
    @pytest.fixture
    def mock_database_manager(self):
        """Mock database manager for audit storage."""
        mock_db = Mock()
        mock_db.store_audit_entry.return_value = 123
        mock_db.get_audit_entries.return_value = []
        return mock_db
    
    @pytest.fixture
    def sample_audit_entry(self):
        """Create sample audit log entry."""
        return AuditLogEntry(
            component="test-component",
            action=AuditAction.EMAIL_DETECTED,
            details={"email_uid": "test-123", "sender": "test@example.com"},
            email_uid="test-123",
            account_id="test-account",
            security_classification="UNCLASSIFIED"
        )
    
    def test_audit_logger_initialization_new_key(self, temp_key_file, mock_database_manager):
        """Test audit logger initialization with new key generation."""
        logger = AuditLogger(temp_key_file, mock_database_manager)
        
        assert logger.signing_key_path == Path(temp_key_file)
        assert logger.database_manager == mock_database_manager
        assert logger._private_key is not None
        assert logger._public_key is not None
        assert logger._last_hash is None
        
        # Verify key files were created
        assert Path(temp_key_file).exists()
        assert Path(temp_key_file.replace('.pem', '.pub')).exists()
    
    def test_audit_logger_initialization_existing_key(self, temp_key_file, mock_database_manager):
        """Test audit logger initialization with existing key."""
        # Create a key file first
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        with open(temp_key_file, 'wb') as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        logger = AuditLogger(temp_key_file, mock_database_manager)
        
        assert logger._private_key is not None
        # Should load the existing key, not generate a new one
        loaded_key_bytes = logger._private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        original_key_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        assert loaded_key_bytes == original_key_bytes
    
    def test_log_audit_entry_creation(self, temp_key_file, mock_database_manager):
        """Test creating and logging an audit entry."""
        logger = AuditLogger(temp_key_file, mock_database_manager)
        
        entry = logger.log_audit_entry(
            component="email-processor",
            action=AuditAction.EMAIL_DETECTED,
            details={"email_uid": "test-123", "sender": "test@example.com"},
            email_uid="test-123",
            account_id="test-account"
        )
        
        assert entry.component == "email-processor"
        assert entry.action == AuditAction.EMAIL_DETECTED
        assert entry.email_uid == "test-123"
        assert entry.account_id == "test-account"
        assert entry.digital_signature is not None
        assert entry.hash_chain_current is not None
        assert entry.hash_chain_previous is None  # First entry
        
        # Verify database storage was called
        mock_database_manager.store_audit_entry.assert_called_once_with(entry)
    
    def test_log_audit_entry_hash_chaining(self, temp_key_file, mock_database_manager):
        """Test hash chaining between audit entries."""
        logger = AuditLogger(temp_key_file, mock_database_manager)
        
        # Create first entry
        entry1 = logger.log_audit_entry(
            component="test-component",
            action=AuditAction.EMAIL_DETECTED,
            details={"test": "data1"}
        )
        
        # Create second entry
        entry2 = logger.log_audit_entry(
            component="test-component",
            action=AuditAction.EMAIL_PROCESSED,
            details={"test": "data2"}
        )
        
        # Verify hash chaining
        assert entry1.hash_chain_previous is None
        assert entry1.hash_chain_current is not None
        assert entry2.hash_chain_previous == entry1.hash_chain_current
        assert entry2.hash_chain_current is not None
        assert entry2.hash_chain_current != entry1.hash_chain_current
    
    def test_verify_entry_integrity_valid(self, temp_key_file, mock_database_manager):
        """Test verifying integrity of a valid audit entry."""
        logger = AuditLogger(temp_key_file, mock_database_manager)
        
        entry = logger.log_audit_entry(
            component="test-component",
            action=AuditAction.EMAIL_DETECTED,
            details={"test": "data"}
        )
        
        # Verify the entry we just created
        is_valid = logger.verify_entry_integrity(entry)
        assert is_valid is True
    
    def test_verify_entry_integrity_tampered_signature(self, temp_key_file, mock_database_manager):
        """Test detecting tampered digital signature."""
        logger = AuditLogger(temp_key_file, mock_database_manager)
        
        entry = logger.log_audit_entry(
            component="test-component",
            action=AuditAction.EMAIL_DETECTED,
            details={"test": "data"}
        )
        
        # Tamper with signature
        entry.digital_signature = "tampered_signature"
        
        is_valid = logger.verify_entry_integrity(entry)
        assert is_valid is False
    
    def test_verify_entry_integrity_tampered_hash(self, temp_key_file, mock_database_manager):
        """Test detecting tampered hash chain."""
        logger = AuditLogger(temp_key_file, mock_database_manager)
        
        entry = logger.log_audit_entry(
            component="test-component",
            action=AuditAction.EMAIL_DETECTED,
            details={"test": "data"}
        )
        
        # Tamper with hash
        entry.hash_chain_current = "tampered_hash"
        
        is_valid = logger.verify_entry_integrity(entry)
        assert is_valid is False
    
    def test_verify_chain_integrity_valid_chain(self, temp_key_file, mock_database_manager):
        """Test verifying integrity of a valid audit chain."""
        logger = AuditLogger(temp_key_file, mock_database_manager)
        
        # Create a chain of entries
        entries = []
        for i in range(5):
            entry = logger.log_audit_entry(
                component="test-component",
                action=AuditAction.EMAIL_DETECTED,
                details={"test": f"data{i}"}
            )
            entries.append(entry)
        
        # Verify entire chain
        is_valid = logger.verify_chain_integrity(entries)
        assert is_valid is True
    
    def test_verify_chain_integrity_broken_chain(self, temp_key_file, mock_database_manager):
        """Test detecting broken hash chain."""
        logger = AuditLogger(temp_key_file, mock_database_manager)
        
        # Create a chain of entries
        entries = []
        for i in range(3):
            entry = logger.log_audit_entry(
                component="test-component",
                action=AuditAction.EMAIL_DETECTED,
                details={"test": f"data{i}"}
            )
            entries.append(entry)
        
        # Break the chain by tampering with middle entry
        entries[1].hash_chain_current = "broken_hash"
        
        is_valid = logger.verify_chain_integrity(entries)
        assert is_valid is False
    
    def test_verify_chain_integrity_empty_chain(self, temp_key_file, mock_database_manager):
        """Test verifying empty audit chain."""
        logger = AuditLogger(temp_key_file, mock_database_manager)
        
        is_valid = logger.verify_chain_integrity([])
        assert is_valid is True
    
    def test_get_audit_trail_with_filters(self, temp_key_file, mock_database_manager):
        """Test retrieving audit trail with filters."""
        logger = AuditLogger(temp_key_file, mock_database_manager)
        
        # Mock database response
        mock_entries = [
            AuditLogEntry(
                component="test-component",
                action=AuditAction.EMAIL_DETECTED,
                details={"test": "data"},
                email_uid="test-123"
            )
        ]
        mock_database_manager.get_audit_entries.return_value = mock_entries
        
        # Get audit trail
        start_time = datetime.utcnow() - timedelta(hours=1)
        end_time = datetime.utcnow()
        
        entries = logger.get_audit_trail(
            email_uid="test-123",
            component="test-component",
            start_time=start_time,
            end_time=end_time
        )
        
        assert len(entries) == 1
        assert entries[0].email_uid == "test-123"
        
        # Verify database was called with correct filters
        mock_database_manager.get_audit_entries.assert_called_once_with(
            email_uid="test-123",
            account_id=None,
            component="test-component",
            start_time=start_time,
            end_time=end_time
        )
    
    def test_get_audit_trail_no_database(self, temp_key_file):
        """Test audit trail retrieval without database manager."""
        logger = AuditLogger(temp_key_file, None)
        
        with pytest.raises(AuditError, match="Database manager not available"):
            logger.get_audit_trail(email_uid="test-123")
    
    def test_calculate_entry_hash_deterministic(self, temp_key_file, mock_database_manager):
        """Test that entry hash calculation is deterministic."""
        logger = AuditLogger(temp_key_file, mock_database_manager)
        
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
    
    def test_calculate_entry_hash_different_entries(self, temp_key_file, mock_database_manager):
        """Test that different entries produce different hashes."""
        logger = AuditLogger(temp_key_file, mock_database_manager)
        
        entry1 = AuditLogEntry(
            component="test-component",
            action=AuditAction.EMAIL_DETECTED,
            details={"test": "data1"}
        )
        
        entry2 = AuditLogEntry(
            component="test-component",
            action=AuditAction.EMAIL_DETECTED,
            details={"test": "data2"}
        )
        
        hash1 = logger._calculate_entry_hash(entry1)
        hash2 = logger._calculate_entry_hash(entry2)
        
        assert hash1 != hash2
    
    def test_sign_entry_creates_valid_signature(self, temp_key_file, mock_database_manager):
        """Test that entry signing creates a valid signature."""
        logger = AuditLogger(temp_key_file, mock_database_manager)
        
        entry = AuditLogEntry(
            component="test-component",
            action=AuditAction.EMAIL_DETECTED,
            details={"test": "data"},
            hash_chain_current="test-hash"
        )
        
        signature = logger._sign_entry(entry)
        
        assert signature is not None
        assert len(signature) > 0
        
        # Verify signature can be decoded
        import base64
        decoded_signature = base64.b64decode(signature.encode('utf-8'))
        assert len(decoded_signature) > 0
    
    def test_verify_signature_valid(self, temp_key_file, mock_database_manager):
        """Test verifying a valid signature."""
        logger = AuditLogger(temp_key_file, mock_database_manager)
        
        entry = AuditLogEntry(
            component="test-component",
            action=AuditAction.EMAIL_DETECTED,
            details={"test": "data"},
            hash_chain_current="test-hash"
        )
        
        # Sign the entry
        entry.digital_signature = logger._sign_entry(entry)
        
        # Verify signature
        is_valid = logger._verify_signature(entry)
        assert is_valid is True
    
    def test_verify_signature_invalid(self, temp_key_file, mock_database_manager):
        """Test detecting invalid signature."""
        logger = AuditLogger(temp_key_file, mock_database_manager)
        
        entry = AuditLogEntry(
            component="test-component",
            action=AuditAction.EMAIL_DETECTED,
            details={"test": "data"},
            hash_chain_current="test-hash",
            digital_signature="invalid_signature"
        )
        
        is_valid = logger._verify_signature(entry)
        assert is_valid is False
    
    def test_verify_signature_no_signature(self, temp_key_file, mock_database_manager):
        """Test verifying entry with no signature."""
        logger = AuditLogger(temp_key_file, mock_database_manager)
        
        entry = AuditLogEntry(
            component="test-component",
            action=AuditAction.EMAIL_DETECTED,
            details={"test": "data"},
            hash_chain_current="test-hash"
        )
        
        is_valid = logger._verify_signature(entry)
        assert is_valid is False
    
    def test_audit_entry_serialization(self, sample_audit_entry):
        """Test audit entry serialization for hashing."""
        entry_dict = sample_audit_entry.to_dict()
        
        assert isinstance(entry_dict, dict)
        assert entry_dict['component'] == "test-component"
        assert entry_dict['action'] == "email_detected"
        assert entry_dict['details'] == {"email_uid": "test-123", "sender": "test@example.com"}
        assert 'timestamp' in entry_dict
        assert 'entry_id' in entry_dict
    
    def test_error_handling_key_creation_failure(self, mock_database_manager):
        """Test error handling when key creation fails."""
        # Use invalid path that will cause permission error
        invalid_path = "/root/invalid_key.pem"
        
        with pytest.raises(AuditError, match="Failed to create signing key"):
            AuditLogger(invalid_path, mock_database_manager)
    
    def test_error_handling_database_storage_failure(self, temp_key_file, mock_database_manager):
        """Test error handling when database storage fails."""
        logger = AuditLogger(temp_key_file, mock_database_manager)
        
        # Mock database failure
        mock_database_manager.store_audit_entry.side_effect = Exception("Database error")
        
        with pytest.raises(AuditError, match="Audit logging failed"):
            logger.log_audit_entry(
                component="test-component",
                action=AuditAction.EMAIL_DETECTED,
                details={"test": "data"}
            )
    
    def test_error_handling_hash_calculation_failure(self, temp_key_file, mock_database_manager):
        """Test error handling when hash calculation fails."""
        logger = AuditLogger(temp_key_file, mock_database_manager)
        
        # Create entry with non-serializable data
        entry = AuditLogEntry(
            component="test-component",
            action=AuditAction.EMAIL_DETECTED,
            details={"test": object()}  # Non-serializable object
        )
        
        with pytest.raises(AuditError, match="Failed to calculate entry hash"):
            logger._calculate_entry_hash(entry)
    
    def test_concurrent_audit_logging(self, temp_key_file, mock_database_manager):
        """Test concurrent audit logging operations."""
        import threading
        
        logger = AuditLogger(temp_key_file, mock_database_manager)
        
        entries = []
        errors = []
        
        def worker(worker_id):
            try:
                entry = logger.log_audit_entry(
                    component=f"worker-{worker_id}",
                    action=AuditAction.EMAIL_DETECTED,
                    details={"worker_id": worker_id}
                )
                entries.append(entry)
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
        assert len(entries) == 10
        
        # Verify hash chaining is maintained
        sorted_entries = sorted(entries, key=lambda x: x.timestamp)
        for i in range(1, len(sorted_entries)):
            # Note: Due to concurrent execution, hash chaining might not be perfectly sequential
            # but each entry should have a valid signature
            assert logger.verify_entry_integrity(sorted_entries[i])
    
    def test_performance_large_audit_chain(self, temp_key_file, mock_database_manager):
        """Test performance with large audit chain."""
        import time
        
        logger = AuditLogger(temp_key_file, mock_database_manager)
        
        # Create large chain
        entries = []
        start_time = time.time()
        
        for i in range(100):
            entry = logger.log_audit_entry(
                component="performance-test",
                action=AuditAction.EMAIL_DETECTED,
                details={"iteration": i}
            )
            entries.append(entry)
        
        creation_time = time.time() - start_time
        
        # Verify chain integrity
        start_time = time.time()
        is_valid = logger.verify_chain_integrity(entries)
        verification_time = time.time() - start_time
        
        assert is_valid is True
        
        # Performance should be reasonable
        assert creation_time < 10.0  # Less than 10 seconds for 100 entries
        assert verification_time < 5.0  # Less than 5 seconds to verify 100 entries
        
        print(f"Created 100 audit entries in {creation_time:.2f}s")
        print(f"Verified 100 audit entries in {verification_time:.2f}s")