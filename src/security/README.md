# Federal-Grade Credential Security System

The Security module provides federal-grade credential management capabilities for the Email Agent system, implementing AES-256 encryption, secure key derivation, automatic credential rotation, and NIST SP 800-63B compliant password validation.

## Features

### 🔐 AES-256-GCM Encryption
- **Algorithm**: AES-256 in Galois/Counter Mode (GCM)
- **Authentication**: Built-in authenticated encryption
- **Key Size**: 256-bit encryption keys
- **Nonce**: Unique 96-bit nonce for each encryption
- **Salt**: Unique 256-bit salt for key derivation

### 🔑 PBKDF2 Key Derivation
- **Algorithm**: PBKDF2-HMAC-SHA256
- **Iterations**: Configurable (default: 100,000)
- **Salt**: Cryptographically secure random salt
- **Key Length**: 256 bits for AES-256

### 🛡️ Federal Password Validation
- **Standard**: NIST SP 800-63B compliant
- **Minimum Length**: 12 characters
- **Maximum Length**: 128 characters
- **Complexity**: Uppercase, lowercase, digits, special characters
- **Pattern Detection**: Common patterns and dictionary words
- **Repetition Check**: Excessive character repetition detection

### 🔄 Automatic Credential Rotation
- **Configurable Intervals**: Default 90 days
- **Secure Backup**: Automatic backup before rotation
- **Failure Recovery**: Rollback on rotation failure
- **Expiration Tracking**: Automatic expiration monitoring

### 🔒 Secure Storage
- **File Permissions**: Restrictive 600 (owner read/write only)
- **Encrypted Storage**: All credentials encrypted at rest
- **Metadata Protection**: Encrypted timestamps and rotation info
- **Integrity Protection**: Cryptographic authentication tags

## Quick Start

```python
from src.security.credential_manager import CredentialManager

# Initialize credential manager
cm = CredentialManager(
    key_file_path="/secure/path/master.key",
    storage_path="/secure/path/credentials",
    kdf_iterations=100000,
    rotation_days=90
)

# Store credentials securely
credentials = {
    "username": "user@example.gov",
    "password": "CompliantP@ssw0rd123!",
    "api_key": "sk-1234567890abcdef"
}

cm.store_encrypted_credentials(credentials, "account_001")

# Load credentials
loaded_creds = cm.load_encrypted_credentials("account_001")

# Rotate credentials
new_credentials = {
    "username": "user@example.gov", 
    "password": "NewCompliantP@ssw0rd456!",
    "api_key": "sk-new-abcdef1234567890"
}

cm.rotate_credentials("account_001", new_credentials)
```

## API Reference

### CredentialManager

#### Constructor
```python
CredentialManager(
    key_file_path: str,
    storage_path: str = "credentials",
    kdf_iterations: int = 100000,
    rotation_days: int = 90
)
```

#### Core Methods

##### encrypt_credentials(credentials, account_id)
Encrypt credentials using AES-256-GCM with unique salt and nonce.

**Parameters:**
- `credentials` (Dict[str, str]): Dictionary of credential key-value pairs
- `account_id` (str): Unique identifier for the account

**Returns:** Base64-encoded encrypted credential data

**Raises:** `EncryptionError` if encryption fails

##### decrypt_credentials(encrypted_data, account_id)
Decrypt credentials using AES-256-GCM.

**Parameters:**
- `encrypted_data` (str): Base64-encoded encrypted credential data
- `account_id` (str): Account identifier for validation

**Returns:** Dictionary of decrypted credentials

**Raises:** `DecryptionError` if decryption fails

##### store_encrypted_credentials(credentials, account_id)
Encrypt and store credentials to secure file storage.

**Parameters:**
- `credentials` (Dict[str, str]): Dictionary of credentials to store
- `account_id` (str): Unique account identifier

**Raises:** `CredentialError` if storage fails

##### load_encrypted_credentials(account_id)
Load and decrypt credentials from secure file storage.

**Parameters:**
- `account_id` (str): Account identifier

**Returns:** Dictionary of decrypted credentials

**Raises:** `CredentialError` if loading fails

##### rotate_credentials(account_id, new_credentials)
Rotate credentials for an account with secure backup.

**Parameters:**
- `account_id` (str): Account identifier
- `new_credentials` (Dict[str, str]): New credentials to store

**Raises:** `RotationError` if rotation fails

##### validate_credential_strength(password)
Validate password meets federal security standards (NIST SP 800-63B).

**Parameters:**
- `password` (str): Password to validate

**Returns:** `True` if password meets federal standards

**Raises:** `StrengthValidationError` if password doesn't meet requirements

##### get_accounts_due_for_rotation()
Get list of account IDs that are due for credential rotation.

**Returns:** List of account IDs requiring rotation

## Security Features

### Encryption Security
- **AES-256-GCM**: Industry-standard authenticated encryption
- **Unique Salts**: Each encryption uses a cryptographically secure random salt
- **Unique Nonces**: Each encryption uses a unique nonce to prevent replay attacks
- **Authentication Tags**: Built-in integrity protection against tampering

### Key Management
- **Master Key**: Securely generated 256-bit master key
- **Key Derivation**: PBKDF2 with configurable iterations (minimum 100,000)
- **Key Storage**: Master key stored with restrictive file permissions
- **Key Rotation**: Support for master key rotation (manual process)

### Password Security
- **Federal Standards**: NIST SP 800-63B compliant validation
- **Complexity Requirements**: Multi-factor complexity validation
- **Pattern Detection**: Common password pattern detection
- **Length Requirements**: Configurable minimum/maximum lengths

### File System Security
- **Restrictive Permissions**: 600 (owner read/write only)
- **Secure Directories**: Automatic creation of secure storage directories
- **Atomic Operations**: Atomic file operations to prevent corruption
- **Backup Management**: Secure backup and recovery procedures

## Error Handling

The module provides comprehensive error handling with specific exception types:

- `SecurityError`: Base exception for security-related errors
- `EncryptionError`: Encryption operation failures
- `DecryptionError`: Decryption operation failures
- `CredentialError`: Credential storage/retrieval failures
- `RotationError`: Credential rotation failures
- `ValidationError`: Security validation failures
- `KeyDerivationError`: Key derivation failures
- `StrengthValidationError`: Password strength validation failures

## Testing

The module includes comprehensive unit tests with security-focused scenarios:

```bash
# Run all security tests
python -m pytest tests/security/ -v

# Run specific test categories
python -m pytest tests/security/test_credential_manager.py::TestCredentialManager -v
python -m pytest tests/security/test_credential_manager.py::TestCredentialManagerThreatSimulation -v
```

### Test Coverage
- ✅ Encryption/decryption operations
- ✅ Password strength validation
- ✅ Credential rotation and recovery
- ✅ File system security
- ✅ Error handling and edge cases
- ✅ Threat simulation scenarios
- ✅ Concurrent access safety
- ✅ Cryptographic integrity

## Compliance

### Federal Standards
- **NIST SP 800-63B**: Digital Identity Guidelines (Authentication)
- **FIPS 140-2**: Cryptographic Module Validation
- **FISMA**: Federal Information Security Management Act
- **FedRAMP**: Federal Risk and Authorization Management Program

### Security Controls
- **AC-2**: Account Management
- **IA-5**: Authenticator Management
- **SC-12**: Cryptographic Key Establishment and Management
- **SC-13**: Cryptographic Protection
- **SC-28**: Protection of Information at Rest

## Performance

### Benchmarks
- **Encryption**: ~1ms per credential set (typical)
- **Decryption**: ~1ms per credential set (typical)
- **Key Derivation**: ~100ms with 100,000 iterations
- **Password Validation**: ~1ms per password

### Scalability
- **Concurrent Access**: Thread-safe operations
- **Memory Usage**: Efficient memory management
- **File I/O**: Optimized file operations
- **Caching**: Minimal memory footprint

## Examples

See `examples/credential_security_demo.py` for a comprehensive demonstration of all security features.

## Dependencies

- `cryptography`: Modern cryptographic library
- `secrets`: Cryptographically secure random number generation
- `pathlib`: Modern path handling
- `json`: JSON serialization
- `base64`: Base64 encoding/decoding
- `hashlib`: Hash functions
- `re`: Regular expressions for validation

## License

This module is part of the U.S. Department of Labor Email Agent system and is subject to federal security requirements and regulations.