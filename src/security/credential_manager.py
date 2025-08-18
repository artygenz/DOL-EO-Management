"""
Federal-Grade Credential Security System for the Email Agent.

Provides AES-256 encryption, secure key derivation, automatic credential rotation,
and federal compliance validation for all credential operations.
"""

import os
import json
import base64
import secrets
import hashlib
import re
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import logging

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend

from .exceptions import (
    EncryptionError, DecryptionError, CredentialError, 
    RotationError, ValidationError, KeyDerivationError,
    StrengthValidationError
)


class CredentialManager:
    """
    Federal-grade credential security manager with AES-256 encryption.
    
    Features:
    - AES-256-GCM encryption for all credential storage
    - PBKDF2 key derivation with configurable iterations
    - Automatic credential rotation with configurable intervals
    - Federal password strength validation (NIST SP 800-63B compliant)
    - Secure key storage and management
    - Comprehensive audit logging for all operations
    """
    
    # Federal password requirements (NIST SP 800-63B)
    FEDERAL_MIN_LENGTH = 12
    FEDERAL_MAX_LENGTH = 128
    FEDERAL_COMPLEXITY_PATTERNS = {
        'uppercase': r'[A-Z]',
        'lowercase': r'[a-z]',
        'digits': r'\d',
        'special': r'[!@#$%^&*(),.?":{}|<>_+=\-\[\]\\;\'\/~`]'
    }
    
    # Key derivation parameters
    DEFAULT_KDF_ITERATIONS = 100000  # NIST recommended minimum
    SALT_LENGTH = 32  # 256 bits
    KEY_LENGTH = 32   # 256 bits for AES-256
    
    # Rotation settings
    DEFAULT_ROTATION_DAYS = 90
    ROTATION_WARNING_DAYS = 7
    
    def __init__(self, 
                 key_file_path: str,
                 storage_path: str = "credentials",
                 kdf_iterations: int = DEFAULT_KDF_ITERATIONS,
                 rotation_days: int = DEFAULT_ROTATION_DAYS):
        """
        Initialize the credential manager.
        
        Args:
            key_file_path: Path to the master key file
            storage_path: Directory for encrypted credential storage
            kdf_iterations: PBKDF2 iterations for key derivation
            rotation_days: Days between automatic credential rotation
        """
        self.logger = logging.getLogger(__name__)
        self.key_file_path = Path(key_file_path)
        self.storage_path = Path(storage_path)
        self.kdf_iterations = kdf_iterations
        self.rotation_days = rotation_days
        
        # Ensure storage directory exists
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize or load master key
        self._master_key = self._load_or_create_master_key()
        
        self.logger.info("Credential manager initialized with federal-grade security")
    
    def encrypt_credentials(self, credentials: Dict[str, str], account_id: str) -> str:
        """
        Encrypt credentials using AES-256-GCM with unique salt and nonce.
        
        Args:
            credentials: Dictionary of credential key-value pairs
            account_id: Unique identifier for the account
            
        Returns:
            Base64-encoded encrypted credential data
            
        Raises:
            EncryptionError: If encryption fails
        """
        try:
            # Validate credentials before encryption
            self._validate_credentials_dict(credentials)
            
            # Generate unique salt and nonce for this encryption
            salt = secrets.token_bytes(self.SALT_LENGTH)
            nonce = secrets.token_bytes(12)  # 96 bits for GCM
            
            # Derive encryption key from master key and salt
            encryption_key = self._derive_key(self._master_key, salt)
            
            # Prepare credential data with metadata
            credential_data = {
                'credentials': credentials,
                'account_id': account_id,
                'encrypted_at': datetime.utcnow().isoformat(),
                'rotation_due': (datetime.utcnow() + timedelta(days=self.rotation_days)).isoformat()
            }
            
            # Serialize to JSON
            plaintext = json.dumps(credential_data).encode('utf-8')
            
            # Encrypt using AES-256-GCM
            cipher = Cipher(
                algorithms.AES(encryption_key),
                modes.GCM(nonce),
                backend=default_backend()
            )
            encryptor = cipher.encryptor()
            ciphertext = encryptor.update(plaintext) + encryptor.finalize()
            
            # Combine salt, nonce, tag, and ciphertext
            encrypted_package = {
                'salt': base64.b64encode(salt).decode('utf-8'),
                'nonce': base64.b64encode(nonce).decode('utf-8'),
                'tag': base64.b64encode(encryptor.tag).decode('utf-8'),
                'ciphertext': base64.b64encode(ciphertext).decode('utf-8'),
                'kdf_iterations': self.kdf_iterations,
                'version': '1.0'
            }
            
            # Encode the entire package
            encrypted_data = base64.b64encode(
                json.dumps(encrypted_package).encode('utf-8')
            ).decode('utf-8')
            
            self.logger.info(f"Credentials encrypted successfully for account: {account_id}")
            return encrypted_data
            
        except Exception as e:
            self.logger.error(f"Credential encryption failed for account {account_id}: {e}")
            raise EncryptionError(f"Failed to encrypt credentials: {e}")
    
    def decrypt_credentials(self, encrypted_data: str, account_id: str) -> Dict[str, str]:
        """
        Decrypt credentials using AES-256-GCM.
        
        Args:
            encrypted_data: Base64-encoded encrypted credential data
            account_id: Account identifier for validation
            
        Returns:
            Dictionary of decrypted credentials
            
        Raises:
            DecryptionError: If decryption fails
        """
        try:
            # Decode the encrypted package
            package_data = json.loads(
                base64.b64decode(encrypted_data.encode('utf-8')).decode('utf-8')
            )
            
            # Extract components
            salt = base64.b64decode(package_data['salt'])
            nonce = base64.b64decode(package_data['nonce'])
            tag = base64.b64decode(package_data['tag'])
            ciphertext = base64.b64decode(package_data['ciphertext'])
            kdf_iterations = package_data.get('kdf_iterations', self.kdf_iterations)
            
            # Derive decryption key
            decryption_key = self._derive_key(self._master_key, salt, kdf_iterations)
            
            # Decrypt using AES-256-GCM
            cipher = Cipher(
                algorithms.AES(decryption_key),
                modes.GCM(nonce, tag),
                backend=default_backend()
            )
            decryptor = cipher.decryptor()
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            
            # Parse decrypted data
            credential_data = json.loads(plaintext.decode('utf-8'))
            
            # Validate account ID matches
            if credential_data.get('account_id') != account_id:
                raise DecryptionError("Account ID mismatch in decrypted data")
            
            # Check if rotation is due
            rotation_due = datetime.fromisoformat(credential_data.get('rotation_due', '1970-01-01'))
            if datetime.utcnow() > rotation_due:
                self.logger.warning(f"Credentials for account {account_id} are due for rotation")
            
            self.logger.info(f"Credentials decrypted successfully for account: {account_id}")
            return credential_data['credentials']
            
        except Exception as e:
            self.logger.error(f"Credential decryption failed for account {account_id}: {e}")
            raise DecryptionError(f"Failed to decrypt credentials: {e}")
    
    def store_encrypted_credentials(self, credentials: Dict[str, str], account_id: str) -> None:
        """
        Encrypt and store credentials to secure file storage.
        
        Args:
            credentials: Dictionary of credentials to store
            account_id: Unique account identifier
            
        Raises:
            CredentialError: If storage fails
        """
        try:
            encrypted_data = self.encrypt_credentials(credentials, account_id)
            
            # Store to secure file
            credential_file = self.storage_path / f"{account_id}.cred"
            with open(credential_file, 'w', encoding='utf-8') as f:
                f.write(encrypted_data)
            
            # Set restrictive file permissions (owner read/write only)
            credential_file.chmod(0o600)
            
            self.logger.info(f"Credentials stored securely for account: {account_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to store credentials for account {account_id}: {e}")
            raise CredentialError(f"Failed to store credentials: {e}")
    
    def load_encrypted_credentials(self, account_id: str) -> Dict[str, str]:
        """
        Load and decrypt credentials from secure file storage.
        
        Args:
            account_id: Account identifier
            
        Returns:
            Dictionary of decrypted credentials
            
        Raises:
            CredentialError: If loading fails
        """
        try:
            credential_file = self.storage_path / f"{account_id}.cred"
            
            if not credential_file.exists():
                raise CredentialError(f"Credential file not found for account: {account_id}")
            
            with open(credential_file, 'r', encoding='utf-8') as f:
                encrypted_data = f.read().strip()
            
            return self.decrypt_credentials(encrypted_data, account_id)
            
        except Exception as e:
            self.logger.error(f"Failed to load credentials for account {account_id}: {e}")
            raise CredentialError(f"Failed to load credentials: {e}")
    
    def rotate_credentials(self, account_id: str, new_credentials: Dict[str, str]) -> None:
        """
        Rotate credentials for an account with secure backup.
        
        Args:
            account_id: Account identifier
            new_credentials: New credentials to store
            
        Raises:
            RotationError: If rotation fails
        """
        try:
            credential_file = self.storage_path / f"{account_id}.cred"
            backup_file = self.storage_path / f"{account_id}.cred.backup"
            
            # Create backup of existing credentials if they exist
            if credential_file.exists():
                credential_file.rename(backup_file)
                self.logger.info(f"Created backup of existing credentials for account: {account_id}")
            
            try:
                # Validate new credentials
                self._validate_credentials_dict(new_credentials)
                
                # Store new credentials
                self.store_encrypted_credentials(new_credentials, account_id)
                
                # Remove backup on successful rotation
                if backup_file.exists():
                    backup_file.unlink()
                
                self.logger.info(f"Credentials rotated successfully for account: {account_id}")
                
            except Exception as e:
                # Restore backup on failure
                if backup_file.exists():
                    backup_file.rename(credential_file)
                    self.logger.info(f"Restored backup credentials for account: {account_id}")
                raise e
                
        except Exception as e:
            self.logger.error(f"Credential rotation failed for account {account_id}: {e}")
            raise RotationError(f"Failed to rotate credentials: {e}")
    
    def validate_credential_strength(self, password: str) -> bool:
        """
        Validate password meets federal security standards (NIST SP 800-63B).
        
        Args:
            password: Password to validate
            
        Returns:
            True if password meets federal standards
            
        Raises:
            StrengthValidationError: If password doesn't meet requirements
        """
        errors = []
        
        # Length requirements
        if len(password) < self.FEDERAL_MIN_LENGTH:
            errors.append(f"Password must be at least {self.FEDERAL_MIN_LENGTH} characters long")
        
        if len(password) > self.FEDERAL_MAX_LENGTH:
            errors.append(f"Password must not exceed {self.FEDERAL_MAX_LENGTH} characters")
        
        # Complexity requirements
        for requirement, pattern in self.FEDERAL_COMPLEXITY_PATTERNS.items():
            if not re.search(pattern, password):
                errors.append(f"Password must contain {requirement} characters")
        
        # Check for common patterns (basic implementation)
        if self._contains_common_patterns(password):
            errors.append("Password contains common patterns and may be easily guessed")
        
        # Check for repeated characters
        if self._has_excessive_repetition(password):
            errors.append("Password contains excessive character repetition")
        
        if errors:
            error_msg = "Password validation failed: " + "; ".join(errors)
            self.logger.warning(f"Password strength validation failed: {error_msg}")
            raise StrengthValidationError(error_msg)
        
        self.logger.info("Password meets federal strength requirements")
        return True
    
    def get_accounts_due_for_rotation(self) -> List[str]:
        """
        Get list of account IDs that are due for credential rotation.
        
        Returns:
            List of account IDs requiring rotation
        """
        due_accounts = []
        
        for credential_file in self.storage_path.glob("*.cred"):
            account_id = credential_file.stem
            
            try:
                # Load and check rotation date
                with open(credential_file, 'r', encoding='utf-8') as f:
                    encrypted_data = f.read().strip()
                
                # Decrypt to check rotation date
                credentials_data = self.decrypt_credentials(encrypted_data, account_id)
                
                # Note: In a real implementation, we'd store metadata separately
                # For now, we'll check file modification time as a proxy
                file_age = datetime.utcnow() - datetime.fromtimestamp(credential_file.stat().st_mtime)
                
                if file_age.days >= self.rotation_days:
                    due_accounts.append(account_id)
                elif file_age.days >= (self.rotation_days - self.ROTATION_WARNING_DAYS):
                    self.logger.warning(f"Account {account_id} credentials will expire soon")
                    
            except Exception as e:
                self.logger.error(f"Failed to check rotation status for account {account_id}: {e}")
        
        return due_accounts
    
    def _load_or_create_master_key(self) -> bytes:
        """Load existing master key or create a new one."""
        if self.key_file_path.exists():
            try:
                with open(self.key_file_path, 'rb') as f:
                    key_data = f.read()
                
                # Verify key length
                if len(key_data) != self.KEY_LENGTH:
                    raise KeyDerivationError("Invalid master key length")
                
                self.logger.info("Master key loaded successfully")
                return key_data
                
            except Exception as e:
                self.logger.error(f"Failed to load master key: {e}")
                raise KeyDerivationError(f"Failed to load master key: {e}")
        else:
            # Generate new master key
            master_key = secrets.token_bytes(self.KEY_LENGTH)
            
            try:
                # Ensure key directory exists
                self.key_file_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Write key with restrictive permissions
                with open(self.key_file_path, 'wb') as f:
                    f.write(master_key)
                
                self.key_file_path.chmod(0o600)
                
                self.logger.info("New master key generated and stored securely")
                return master_key
                
            except Exception as e:
                self.logger.error(f"Failed to create master key: {e}")
                raise KeyDerivationError(f"Failed to create master key: {e}")
    
    def _derive_key(self, master_key: bytes, salt: bytes, iterations: Optional[int] = None) -> bytes:
        """Derive encryption key using PBKDF2."""
        try:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=self.KEY_LENGTH,
                salt=salt,
                iterations=iterations or self.kdf_iterations,
                backend=default_backend()
            )
            return kdf.derive(master_key)
            
        except Exception as e:
            raise KeyDerivationError(f"Key derivation failed: {e}")
    
    def _validate_credentials_dict(self, credentials: Dict[str, str]) -> None:
        """Validate credentials dictionary structure."""
        if not isinstance(credentials, dict):
            raise ValidationError("Credentials must be a dictionary")
        
        if not credentials:
            raise ValidationError("Credentials dictionary cannot be empty")
        
        for key, value in credentials.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise ValidationError("All credential keys and values must be strings")
            
            if not key.strip():
                raise ValidationError("Credential keys cannot be empty")
            
            if not value.strip():
                raise ValidationError("Credential values cannot be empty")
            
            # Validate password strength for password fields
            if 'password' in key.lower():
                self.validate_credential_strength(value)
    
    def _contains_common_patterns(self, password: str) -> bool:
        """Check for common password patterns."""
        # Convert to lowercase for pattern checking
        lower_password = password.lower()
        
        # Common patterns to avoid
        common_patterns = [
            'password', 'admin', 'user', 'login', 'welcome',
            '123456', 'qwerty', 'abc123', 'letmein', 'monkey'
        ]
        
        for pattern in common_patterns:
            if pattern in lower_password:
                return True
        
        # Check for keyboard patterns
        keyboard_patterns = ['qwerty', 'asdf', 'zxcv', '1234', 'abcd']
        for pattern in keyboard_patterns:
            if pattern in lower_password:
                return True
        
        return False
    
    def _has_excessive_repetition(self, password: str) -> bool:
        """Check for excessive character repetition."""
        # Check for more than 3 consecutive identical characters
        for i in range(len(password) - 3):
            if password[i] == password[i+1] == password[i+2] == password[i+3]:
                return True
        
        return False