#!/usr/bin/env python3
"""
Federal-Grade Credential Security System Demo

This example demonstrates the key features of the CredentialManager:
- AES-256 encryption/decryption
- Federal password strength validation
- Secure credential storage and rotation
- Key derivation and security controls
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.security.credential_manager import CredentialManager
from src.security.exceptions import StrengthValidationError, CredentialError


def main():
    """Demonstrate credential security system capabilities."""
    print("🔐 Federal-Grade Credential Security System Demo")
    print("=" * 60)
    
    # Create temporary directory for demo
    temp_dir = tempfile.mkdtemp()
    key_file = os.path.join(temp_dir, "demo_master.key")
    storage_path = os.path.join(temp_dir, "demo_credentials")
    
    try:
        # Initialize credential manager
        print("\n1. Initializing Credential Manager...")
        cm = CredentialManager(
            key_file_path=key_file,
            storage_path=storage_path,
            kdf_iterations=10000,  # Reduced for demo speed
            rotation_days=90
        )
        print("✅ Credential manager initialized with federal-grade security")
        
        # Demonstrate password strength validation
        print("\n2. Federal Password Strength Validation...")
        
        # Test weak passwords
        weak_passwords = [
            "password123",      # Common pattern
            "short",           # Too short
            "nouppercase123!", # Missing uppercase
            "NOLOWERCASE123!", # Missing lowercase
        ]
        
        for weak_password in weak_passwords:
            try:
                cm.validate_credential_strength(weak_password)
                print(f"❌ Weak password '{weak_password}' incorrectly passed validation")
            except StrengthValidationError as e:
                print(f"✅ Weak password '{weak_password}' correctly rejected: {str(e)[:50]}...")
        
        # Test strong password
        strong_password = "Compliant123!@#FederalGrade456$%^"
        try:
            cm.validate_credential_strength(strong_password)
            print(f"✅ Strong password passed federal validation")
        except StrengthValidationError as e:
            print(f"❌ Strong password incorrectly rejected: {e}")
        
        # Demonstrate credential encryption and storage
        print("\n3. Credential Encryption and Storage...")
        
        sample_credentials = {
            "username": "federal.user@dol.gov",
            "password": strong_password,
            "api_key": "sk-fed-1234567890abcdef",
            "oauth_token": "oauth2-federal-token-xyz789"
        }
        
        account_id = "dol_email_account_001"
        
        # Encrypt and store credentials
        print(f"   Encrypting credentials for account: {account_id}")
        cm.store_encrypted_credentials(sample_credentials, account_id)
        print("✅ Credentials encrypted and stored securely")
        
        # Verify file permissions
        credential_file = Path(storage_path) / f"{account_id}.cred"
        file_mode = oct(credential_file.stat().st_mode)[-3:]
        print(f"   File permissions: {file_mode} (should be 600 for security)")
        
        # Load and decrypt credentials
        print("   Loading and decrypting credentials...")
        loaded_credentials = cm.load_encrypted_credentials(account_id)
        
        if loaded_credentials == sample_credentials:
            print("✅ Credentials successfully decrypted and verified")
        else:
            print("❌ Credential decryption failed - data mismatch")
        
        # Demonstrate encryption uniqueness
        print("\n4. Encryption Uniqueness (Salt/Nonce Randomization)...")
        
        encrypted1 = cm.encrypt_credentials(sample_credentials, account_id)
        encrypted2 = cm.encrypt_credentials(sample_credentials, account_id)
        
        if encrypted1 != encrypted2:
            print("✅ Multiple encryptions produce unique ciphertext (secure)")
        else:
            print("❌ Multiple encryptions produce identical ciphertext (insecure)")
        
        # Verify both decrypt to same plaintext
        decrypted1 = cm.decrypt_credentials(encrypted1, account_id)
        decrypted2 = cm.decrypt_credentials(encrypted2, account_id)
        
        if decrypted1 == decrypted2 == sample_credentials:
            print("✅ Both unique encryptions decrypt to correct plaintext")
        else:
            print("❌ Decryption consistency failed")
        
        # Demonstrate credential rotation
        print("\n5. Secure Credential Rotation...")
        
        new_credentials = {
            "username": "federal.user@dol.gov",
            "password": "Updated123!@#NewCompliant456$%^",
            "api_key": "sk-fed-new-abcdef1234567890",
            "oauth_token": "oauth2-federal-new-token-abc123"
        }
        
        print("   Rotating credentials with secure backup...")
        cm.rotate_credentials(account_id, new_credentials)
        print("✅ Credentials rotated successfully")
        
        # Verify new credentials are active
        current_credentials = cm.load_encrypted_credentials(account_id)
        if current_credentials == new_credentials:
            print("✅ New credentials are active and accessible")
        else:
            print("❌ Credential rotation verification failed")
        
        # Demonstrate rotation failure recovery
        print("\n6. Rotation Failure Recovery...")
        
        invalid_credentials = {
            "username": "test@example.com",
            "password": "weak",  # Will fail validation
        }
        
        try:
            cm.rotate_credentials(account_id, invalid_credentials)
            print("❌ Invalid credentials incorrectly accepted")
        except Exception as e:
            print(f"✅ Invalid credentials correctly rejected: {str(e)[:50]}...")
            
            # Verify original credentials are still accessible
            recovered_credentials = cm.load_encrypted_credentials(account_id)
            if recovered_credentials == new_credentials:
                print("✅ Original credentials successfully recovered after failed rotation")
            else:
                print("❌ Credential recovery failed")
        
        # Demonstrate key derivation security
        print("\n7. Key Derivation Security...")
        
        # Show that different salts produce different keys
        master_key = cm._master_key
        salt1 = b"salt1" + b"0" * 27  # 32 bytes
        salt2 = b"salt2" + b"0" * 27  # 32 bytes
        
        key1 = cm._derive_key(master_key, salt1)
        key2 = cm._derive_key(master_key, salt2)
        
        if key1 != key2:
            print("✅ Different salts produce different derived keys (secure)")
        else:
            print("❌ Different salts produce identical keys (insecure)")
        
        # Security summary
        print("\n" + "=" * 60)
        print("🛡️  SECURITY FEATURES DEMONSTRATED:")
        print("   ✅ AES-256-GCM encryption with authentication")
        print("   ✅ PBKDF2 key derivation with configurable iterations")
        print("   ✅ Federal password strength validation (NIST SP 800-63B)")
        print("   ✅ Secure random salt and nonce generation")
        print("   ✅ File system security with restrictive permissions")
        print("   ✅ Automatic credential rotation with failure recovery")
        print("   ✅ Cryptographic integrity protection")
        print("   ✅ Secure key management and storage")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Cleanup temporary files
        try:
            shutil.rmtree(temp_dir)
            print(f"\n🧹 Cleaned up temporary files: {temp_dir}")
        except Exception as e:
            print(f"⚠️  Failed to cleanup temporary files: {e}")


if __name__ == "__main__":
    main()