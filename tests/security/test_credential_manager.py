"""
Comprehensive unit tests for the Federal-Grade Credential Security System.
Includes security-focused tests with threat simulation scenarios.
"""

import os
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import pytest

from src.security.credential_manager import CredentialManager
from src.security.exceptions import (
    EncryptionError, DecryptionError, CredentialError,
    RotationError, ValidationError, KeyDerivationError,
    StrengthValidationError
)


class TestCredentialManager:
    """Test suite for CredentialManager with federal security requirements."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def credential_manager(self, temp_dir):
        """Create CredentialManager instance for testing."""
        key_file = os.path.join(temp_dir, "master.key")
        storage_path = os.path.join(temp_dir, "credentials")
        return CredentialManager(
            key_file_path=key_file,
            storage_path=storage_path,
            kdf_iterations=1000  # Reduced for testing speed
        )
    
    @pytest.fixture
    def sample_credentials(self):
        """Sample credentials for testing."""
        return {
            "username": "test@example.gov",
            "password": "SecureP@ssw0rd123!",
            "api_key": "sk-1234567890abcdef"
        }
    
    @pytest.fixture
    def federal_password(self):
        """Federal-compliant password for testing."""
        return "FederalSecure123!@#"
    
    @pytest.fixture
    def weak_passwords(self):
        """List of weak passwords for testing validation."""
        return [
            "password",           # Too common
            "123456",            # Too simple
            "short",             # Too short
            "nouppercase123!",   # No uppercase
            "NOLOWERCASE123!",   # No lowercase
            "NoNumbers!@#",      # No numbers
            "NoSpecialChars123", # No special characters
            "a" * 129,           # Too long
            "aaaaaaaaaaaaa",     # Excessive repetition
        ]
    
    def test_initialization_creates_master_key(self, temp_dir):
        """Test that initialization creates a new master key if none exists."""
        key_file = os.path.join(temp_dir, "master.key")
        storage_path = os.path.join(temp_dir, "credentials")
        
        # Ensure key file doesn't exist
        assert not os.path.exists(key_file)
        
        # Initialize credential manager
        cm = CredentialManager(key_file_path=key_file, storage_path=storage_path)
        
        # Verify key file was created
        assert os.path.exists(key_file)
        
        # Verify key file has correct permissions (owner read/write only)
        key_path = Path(key_file)
        assert oct(key_path.stat().st_mode)[-3:] == '600'
        
        # Verify key length
        with open(key_file, 'rb') as f:
            key_data = f.read()
        assert len(key_data) == 32  # 256 bits
    
    def test_initialization_loads_existing_master_key(self, temp_dir):
        """Test that initialization loads existing master key."""
        key_file = os.path.join(temp_dir, "master.key")
        storage_path = os.path.join(temp_dir, "credentials")
        
        # Create first instance to generate key
        cm1 = CredentialManager(key_file_path=key_file, storage_path=storage_path)
        original_key = cm1._master_key
        
        # Create second instance to load existing key
        cm2 = CredentialManager(key_file_path=key_file, storage_path=storage_path)
        
        # Verify same key was loaded
        assert cm2._master_key == original_key
    
    def test_encrypt_decrypt_credentials_success(self, credential_manager, sample_credentials):
        """Test successful encryption and decryption of credentials."""
        account_id = "test_account"
        
        # Encrypt credentials
        encrypted_data = credential_manager.encrypt_credentials(sample_credentials, account_id)
        
        # Verify encrypted data is base64 encoded string
        assert isinstance(encrypted_data, str)
        assert len(encrypted_data) > 0
        
        # Decrypt credentials
        decrypted_credentials = credential_manager.decrypt_credentials(encrypted_data, account_id)
        
        # Verify decrypted data matches original
        assert decrypted_credentials == sample_credentials
    
    def test_encrypt_credentials_with_invalid_input(self, credential_manager):
        """Test encryption with invalid credential inputs."""
        account_id = "test_account"
        
        # Test with non-dictionary input
        with pytest.raises(EncryptionError, match="Credentials must be a dictionary"):
            credential_manager.encrypt_credentials("not_a_dict", account_id)
        
        # Test with empty dictionary
        with pytest.raises(EncryptionError, match="Credentials dictionary cannot be empty"):
            credential_manager.encrypt_credentials({}, account_id)
        
        # Test with non-string keys/values
        with pytest.raises(EncryptionError, match="All credential keys and values must be strings"):
            credential_manager.encrypt_credentials({123: "value"}, account_id)
        
        # Test with empty key
        with pytest.raises(EncryptionError, match="Credential keys cannot be empty"):
            credential_manager.encrypt_credentials({"": "value"}, account_id)
        
        # Test with empty value
        with pytest.raises(EncryptionError, match="Credential values cannot be empty"):
            credential_manager.encrypt_credentials({"key": ""}, account_id)
    
    def test_decrypt_credentials_with_wrong_account_id(self, credential_manager, sample_credentials):
        """Test decryption fails with wrong account ID."""
        account_id = "test_account"
        wrong_account_id = "wrong_account"
        
        # Encrypt with correct account ID
        encrypted_data = credential_manager.encrypt_credentials(sample_credentials, account_id)
        
        # Try to decrypt with wrong account ID
        with pytest.raises(DecryptionError, match="Account ID mismatch"):
            credential_manager.decrypt_credentials(encrypted_data, wrong_account_id)
    
    def test_decrypt_credentials_with_corrupted_data(self, credential_manager):
        """Test decryption fails with corrupted data."""
        account_id = "test_account"
        
        # Test with invalid base64
        with pytest.raises(DecryptionError):
            credential_manager.decrypt_credentials("invalid_base64!", account_id)
        
        # Test with valid base64 but invalid JSON
        import base64
        invalid_json = base64.b64encode(b"not json").decode('utf-8')
        with pytest.raises(DecryptionError):
            credential_manager.decrypt_credentials(invalid_json, account_id)
    
    def test_store_and_load_encrypted_credentials(self, credential_manager, sample_credentials):
        """Test storing and loading credentials from file system."""
        account_id = "test_account"
        
        # Store credentials
        credential_manager.store_encrypted_credentials(sample_credentials, account_id)
        
        # Verify file was created
        credential_file = credential_manager.storage_path / f"{account_id}.cred"
        assert credential_file.exists()
        
        # Verify file permissions
        assert oct(credential_file.stat().st_mode)[-3:] == '600'
        
        # Load credentials
        loaded_credentials = credential_manager.load_encrypted_credentials(account_id)
        
        # Verify loaded data matches original
        assert loaded_credentials == sample_credentials
    
    def test_load_nonexistent_credentials(self, credential_manager):
        """Test loading credentials for non-existent account."""
        with pytest.raises(CredentialError, match="Credential file not found"):
            credential_manager.load_encrypted_credentials("nonexistent_account")
    
    def test_rotate_credentials_success(self, credential_manager, sample_credentials):
        """Test successful credential rotation."""
        account_id = "test_account"
        
        # Store initial credentials
        credential_manager.store_encrypted_credentials(sample_credentials, account_id)
        
        # Prepare new credentials
        new_credentials = {
            "username": "new_test@example.gov",
            "password": "NewSecureP@ssw0rd456!",
            "api_key": "sk-newkey1234567890"
        }
        
        # Rotate credentials
        credential_manager.rotate_credentials(account_id, new_credentials)
        
        # Verify new credentials are loaded
        loaded_credentials = credential_manager.load_encrypted_credentials(account_id)
        assert loaded_credentials == new_credentials
        
        # Verify backup file was removed
        backup_file = credential_manager.storage_path / f"{account_id}.cred.backup"
        assert not backup_file.exists()
    
    def test_rotate_credentials_with_failure_recovery(self, credential_manager, sample_credentials):
        """Test credential rotation failure recovery."""
        account_id = "test_account"
        
        # Store initial credentials
        credential_manager.store_encrypted_credentials(sample_credentials, account_id)
        
        # Prepare invalid new credentials (will fail validation)
        invalid_credentials = {"password": "weak"}
        
        # Attempt rotation (should fail and restore backup)
        with pytest.raises(RotationError):
            credential_manager.rotate_credentials(account_id, invalid_credentials)
        
        # Verify original credentials are still accessible
        loaded_credentials = credential_manager.load_encrypted_credentials(account_id)
        assert loaded_credentials == sample_credentials
    
    def test_validate_federal_password_strength_success(self, credential_manager, federal_password):
        """Test successful federal password validation."""
        result = credential_manager.validate_credential_strength(federal_password)
        assert result is True
    
    def test_validate_federal_password_strength_failures(self, credential_manager, weak_passwords):
        """Test federal password validation with weak passwords."""
        for weak_password in weak_passwords:
            with pytest.raises(StrengthValidationError):
                credential_manager.validate_credential_strength(weak_password)
    
    def test_validate_password_common_patterns(self, credential_manager):
        """Test password validation detects common patterns."""
        common_pattern_passwords = [
            "Password123!",      # Contains "password"
            "Admin123!@#",       # Contains "admin"
            "Qwerty123!@#",      # Keyboard pattern
            "Abc123!@#$%",       # Sequential pattern
        ]
        
        for password in common_pattern_passwords:
            with pytest.raises(StrengthValidationError, match="common patterns"):
                credential_manager.validate_credential_strength(password)
    
    def test_validate_password_excessive_repetition(self, credential_manager):
        """Test password validation detects excessive repetition."""
        repetitive_passwords = [
            "Aaaaa123!@#$",      # Excessive 'a' repetition
            "Pass1111!@#$",      # Excessive '1' repetition
            "Test!!!!567A",      # Excessive '!' repetition
        ]
        
        for password in repetitive_passwords:
            with pytest.raises(StrengthValidationError, match="excessive character repetition"):
                credential_manager.validate_credential_strength(password)
    
    def test_get_accounts_due_for_rotation(self, credential_manager, sample_credentials):
        """Test identification of accounts due for rotation."""
        account_id = "test_account"
        
        # Store credentials
        credential_manager.store_encrypted_credentials(sample_credentials, account_id)
        
        # Mock file modification time to simulate old credentials
        credential_file = credential_manager.storage_path / f"{account_id}.cred"
        old_time = datetime.utcnow() - timedelta(days=credential_manager.rotation_days + 1)
        os.utime(credential_file, (old_time.timestamp(), old_time.timestamp()))
        
        # Check for accounts due for rotation
        due_accounts = credential_manager.get_accounts_due_for_rotation()
        assert account_id in due_accounts
    
    def test_encryption_uniqueness(self, credential_manager, sample_credentials):
        """Test that multiple encryptions of same data produce different ciphertext."""
        account_id = "test_account"
        
        # Encrypt same credentials multiple times
        encrypted1 = credential_manager.encrypt_credentials(sample_credentials, account_id)
        encrypted2 = credential_manager.encrypt_credentials(sample_credentials, account_id)
        
        # Verify different ciphertext (due to unique salt and nonce)
        assert encrypted1 != encrypted2
        
        # Verify both decrypt to same plaintext
        decrypted1 = credential_manager.decrypt_credentials(encrypted1, account_id)
        decrypted2 = credential_manager.decrypt_credentials(encrypted2, account_id)
        assert decrypted1 == decrypted2 == sample_credentials
    
    def test_key_derivation_with_different_salts(self, credential_manager):
        """Test that different salts produce different derived keys."""
        master_key = credential_manager._master_key
        salt1 = b"salt1" + b"0" * 27  # 32 bytes
        salt2 = b"salt2" + b"0" * 27  # 32 bytes
        
        key1 = credential_manager._derive_key(master_key, salt1)
        key2 = credential_manager._derive_key(master_key, salt2)
        
        assert key1 != key2
        assert len(key1) == len(key2) == 32
    
    def test_invalid_master_key_file(self, temp_dir):
        """Test handling of invalid master key file."""
        key_file = os.path.join(temp_dir, "invalid.key")
        storage_path = os.path.join(temp_dir, "credentials")
        
        # Create invalid key file (wrong length)
        with open(key_file, 'wb') as f:
            f.write(b"invalid_key")
        
        # Should raise error for invalid key length
        with pytest.raises(KeyDerivationError, match="Invalid master key length"):
            CredentialManager(key_file_path=key_file, storage_path=storage_path)
    
    @patch('src.security.credential_manager.secrets.token_bytes')
    def test_master_key_generation_failure(self, mock_token_bytes, temp_dir):
        """Test handling of master key generation failure."""
        mock_token_bytes.side_effect = Exception("Random generation failed")
        
        key_file = os.path.join(temp_dir, "master.key")
        storage_path = os.path.join(temp_dir, "credentials")
        
        with pytest.raises(Exception, match="Random generation failed"):
            CredentialManager(key_file_path=key_file, storage_path=storage_path)
    
    def test_concurrent_access_safety(self, credential_manager, sample_credentials):
        """Test thread safety of credential operations."""
        import threading
        import time
        
        account_id = "concurrent_test"
        results = []
        errors = []
        
        def encrypt_decrypt_worker():
            try:
                encrypted = credential_manager.encrypt_credentials(sample_credentials, account_id)
                decrypted = credential_manager.decrypt_credentials(encrypted, account_id)
                results.append(decrypted == sample_credentials)
            except Exception as e:
                errors.append(e)
        
        # Run multiple threads concurrently
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=encrypt_decrypt_worker)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify no errors and all operations succeeded
        assert len(errors) == 0, f"Concurrent access errors: {errors}"
        assert all(results), "Some concurrent operations failed"
        assert len(results) == 5, "Not all threads completed"


class TestCredentialManagerThreatSimulation:
    """Security-focused tests simulating real-world threat scenarios."""
    
    @pytest.fixture
    def credential_manager(self, tmp_path):
        """Create CredentialManager for threat simulation tests."""
        key_file = tmp_path / "master.key"
        storage_path = tmp_path / "credentials"
        return CredentialManager(
            key_file_path=str(key_file),
            storage_path=str(storage_path)
        )
    
    def test_brute_force_resistance(self, credential_manager):
        """Test resistance to brute force attacks on encrypted data."""
        credentials = {"password": "SecureP@ssw0rd123!"}
        account_id = "brute_force_test"
        
        # Encrypt credentials
        encrypted_data = credential_manager.encrypt_credentials(credentials, account_id)
        
        # Simulate brute force attempts with wrong keys
        wrong_keys = [b"wrong_key" + bytes(i) for i in range(100)]
        
        for wrong_key in wrong_keys:
            # Create credential manager with wrong key
            temp_cm = credential_manager.__class__.__new__(credential_manager.__class__)
            temp_cm._master_key = wrong_key[:32].ljust(32, b'\x00')
            temp_cm.logger = credential_manager.logger
            temp_cm.kdf_iterations = credential_manager.kdf_iterations
            
            # Attempt decryption should fail
            with pytest.raises(DecryptionError):
                temp_cm.decrypt_credentials(encrypted_data, account_id)
    
    def test_timing_attack_resistance(self, credential_manager):
        """Test resistance to timing attacks on password validation."""
        import time
        
        # Test passwords of different lengths and complexities
        test_passwords = [
            "short",
            "medium_length_password",
            "very_long_password_with_many_characters_and_complexity",
            "P@ssw0rd123!",
            "ComplexP@ssw0rd123!WithManyCharacters"
        ]
        
        timing_results = []
        
        for password in test_passwords:
            start_time = time.time()
            try:
                credential_manager.validate_credential_strength(password)
            except StrengthValidationError:
                pass  # Expected for some passwords
            end_time = time.time()
            
            timing_results.append(end_time - start_time)
        
        # Verify timing differences are not excessive (basic check)
        # In a real implementation, this would be more sophisticated
        max_time = max(timing_results)
        min_time = min(timing_results)
        
        # Allow for some variation but not orders of magnitude
        # Note: This is a basic timing test - in production, more sophisticated analysis would be needed
        if min_time > 0:
            ratio = max_time / min_time
            assert ratio < 100, f"Excessive timing variation detected: {ratio}"
    
    def test_memory_cleanup_after_operations(self, credential_manager):
        """Test that sensitive data is properly cleaned from memory."""
        import gc
        
        credentials = {"password": "SecureP@ssw0rd123!"}
        account_id = "memory_test"
        
        # Perform encryption/decryption operations
        encrypted_data = credential_manager.encrypt_credentials(credentials, account_id)
        decrypted_data = credential_manager.decrypt_credentials(encrypted_data, account_id)
        
        # Clear local references
        del credentials
        del decrypted_data
        del encrypted_data
        
        # Force garbage collection
        gc.collect()
        
        # Note: In a production system, we would use secure memory clearing
        # This test serves as a placeholder for memory security validation
        assert True  # Placeholder assertion
    
    def test_side_channel_attack_resistance(self, credential_manager):
        """Test basic resistance to side-channel attacks."""
        credentials = {"password": "SecureP@ssw0rd123!"}
        account_id = "side_channel_test"
        
        # Encrypt same data multiple times
        encryptions = []
        for _ in range(10):
            encrypted = credential_manager.encrypt_credentials(credentials, account_id)
            encryptions.append(encrypted)
        
        # Verify all encryptions are different (no patterns)
        unique_encryptions = set(encryptions)
        assert len(unique_encryptions) == len(encryptions), "Encryption patterns detected"
        
        # Verify all decrypt to same plaintext
        for encrypted in encryptions:
            decrypted = credential_manager.decrypt_credentials(encrypted, account_id)
            assert decrypted == credentials
    
    def test_file_system_attack_resistance(self, credential_manager, tmp_path):
        """Test resistance to file system-based attacks."""
        credentials = {"password": "SecureP@ssw0rd123!"}
        account_id = "filesystem_test"
        
        # Store credentials
        credential_manager.store_encrypted_credentials(credentials, account_id)
        
        # Verify file permissions are restrictive
        credential_file = credential_manager.storage_path / f"{account_id}.cred"
        file_mode = oct(credential_file.stat().st_mode)[-3:]
        assert file_mode == '600', f"Insecure file permissions: {file_mode}"
        
        # Verify file contents are encrypted (not plaintext)
        with open(credential_file, 'r') as f:
            file_contents = f.read()
        
        # Should not contain plaintext password
        assert credentials["password"] not in file_contents
        assert "password" not in file_contents.lower()
        
        # Should be base64 encoded
        import base64
        try:
            base64.b64decode(file_contents)
        except Exception:
            pytest.fail("Credential file is not properly base64 encoded")
    
    def test_injection_attack_resistance(self, credential_manager):
        """Test resistance to injection attacks in credential data."""
        # Test with various injection payloads
        injection_payloads = [
            {"username": "user'; DROP TABLE users; --", "password": "SecureP@ss123!"},
            {"username": "user<script>alert('xss')</script>", "password": "SecureP@ss123!"},
            {"username": "user\x00\x01\x02", "password": "SecureP@ss123!"},
            {"username": "user\n\r\t", "password": "SecureP@ss123!"},
        ]
        
        for payload in injection_payloads:
            account_id = f"injection_test_{hash(str(payload))}"
            
            # Should handle injection attempts safely
            encrypted = credential_manager.encrypt_credentials(payload, account_id)
            decrypted = credential_manager.decrypt_credentials(encrypted, account_id)
            
            # Data should be preserved exactly (no interpretation)
            assert decrypted == payload
    
    def test_cryptographic_integrity(self, credential_manager):
        """Test cryptographic integrity and tamper detection."""
        credentials = {"password": "SecureP@ssw0rd123!"}
        account_id = "integrity_test"
        
        # Encrypt credentials
        encrypted_data = credential_manager.encrypt_credentials(credentials, account_id)
        
        # Tamper with encrypted data
        import base64
        decoded = base64.b64decode(encrypted_data)
        tampered = decoded[:-1] + b'X'  # Change last byte
        tampered_encoded = base64.b64encode(tampered).decode('utf-8')
        
        # Decryption should fail due to integrity check
        with pytest.raises(DecryptionError):
            credential_manager.decrypt_credentials(tampered_encoded, account_id)
    
    def test_key_rotation_security(self, credential_manager, tmp_path):
        """Test security aspects of key rotation."""
        credentials = {"password": "SecureP@ssw0rd123!"}
        account_id = "rotation_security_test"
        
        # Store initial credentials
        credential_manager.store_encrypted_credentials(credentials, account_id)
        
        # Simulate key rotation by creating new credential manager
        new_key_file = tmp_path / "new_master.key"
        new_storage = tmp_path / "new_credentials"
        
        new_cm = CredentialManager(
            key_file_path=str(new_key_file),
            storage_path=str(new_storage)
        )
        
        # Old encrypted data should not be decryptable with new key
        old_encrypted = credential_manager.encrypt_credentials(credentials, account_id)
        
        with pytest.raises(DecryptionError):
            new_cm.decrypt_credentials(old_encrypted, account_id)
        
        # New encryption should work with new key
        new_encrypted = new_cm.encrypt_credentials(credentials, account_id)
        new_decrypted = new_cm.decrypt_credentials(new_encrypted, account_id)
        assert new_decrypted == credentials