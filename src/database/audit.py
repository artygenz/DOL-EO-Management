"""
Immutable audit logging system with cryptographic signing.

Provides federal-grade audit logging with:
- Cryptographic signing for tamper detection
- Hash chain integrity verification
- Immutable log entries
- Complete traceability of all operations
"""

import hashlib
import hmac
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend

from .models import AuditLogEntry, AuditAction
from .exceptions import AuditError


class AuditLogger:
    """
    Federal-grade audit logger with cryptographic signing and hash chaining.
    
    Features:
    - RSA digital signatures for entry authenticity
    - SHA-256 hash chaining for integrity verification
    - Immutable log entries with tamper detection
    - Complete audit trail for compliance requirements
    """
    
    def __init__(self, 
                 signing_key_path: str,
                 database_manager=None,
                 hash_algorithm: str = 'sha256'):
        """
        Initialize the audit logger.
        
        Args:
            signing_key_path: Path to RSA private key for signing
            database_manager: Database manager instance for log storage
            hash_algorithm: Hash algorithm for chain integrity
        """
        self.logger = logging.getLogger(__name__)
        self.signing_key_path = Path(signing_key_path)
        self.database_manager = database_manager
        self.hash_algorithm = hash_algorithm
        
        # Load or generate signing key
        self._private_key = self._load_or_create_signing_key()
        self._public_key = self._private_key.public_key()
        
        # Track last hash for chain integrity
        self._last_hash: Optional[str] = None
        
        self.logger.info("Audit logger initialized with cryptographic signing")
    
    def log_audit_entry(self, 
                       component: str,
                       action: AuditAction,
                       details: Dict[str, Any],
                       email_uid: Optional[str] = None,
                       account_id: Optional[str] = None,
                       user_id: Optional[str] = None,
                       security_classification: str = "UNCLASSIFIED") -> AuditLogEntry:
        """
        Create and store a cryptographically signed audit log entry.
        
        Args:
            component: System component generating the log
            action: Type of action being audited
            details: Additional details about the action
            email_uid: Associated email UID if applicable
            account_id: Associated account ID if applicable
            user_id: User ID if applicable
            security_classification: Security classification level
            
        Returns:
            Created audit log entry
            
        Raises:
            AuditError: If audit logging fails
        """
        try:
            # Create audit entry
            entry = AuditLogEntry(
                component=component,
                action=action,
                details=details,
                email_uid=email_uid,
                account_id=account_id,
                user_id=user_id,
                security_classification=security_classification,
                hash_chain_previous=self._last_hash
            )
            
            # Calculate hash chain
            entry.hash_chain_current = self._calculate_entry_hash(entry)
            
            # Sign the entry
            entry.digital_signature = self._sign_entry(entry)
            
            # Store in database if available
            if self.database_manager:
                self.database_manager.store_audit_entry(entry)
            
            # Update hash chain
            self._last_hash = entry.hash_chain_current
            
            self.logger.debug(f"Audit entry created: {entry.entry_id}")
            return entry
            
        except Exception as e:
            self.logger.error(f"Failed to create audit entry: {e}")
            raise AuditError(f"Audit logging failed: {e}")
    
    def verify_entry_integrity(self, entry: AuditLogEntry) -> bool:
        """
        Verify the cryptographic integrity of an audit log entry.
        
        Args:
            entry: Audit log entry to verify
            
        Returns:
            True if entry is authentic and unmodified
        """
        try:
            # Verify digital signature
            if not self._verify_signature(entry):
                self.logger.warning(f"Digital signature verification failed for entry: {entry.entry_id}")
                return False
            
            # Verify hash chain
            calculated_hash = self._calculate_entry_hash(entry)
            if calculated_hash != entry.hash_chain_current:
                self.logger.warning(f"Hash chain verification failed for entry: {entry.entry_id}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Entry integrity verification failed: {e}")
            return False
    
    def verify_chain_integrity(self, entries: List[AuditLogEntry]) -> bool:
        """
        Verify the integrity of an entire audit log chain.
        
        Args:
            entries: List of audit entries in chronological order
            
        Returns:
            True if entire chain is valid
        """
        try:
            if not entries:
                return True
            
            # Sort entries by timestamp
            sorted_entries = sorted(entries, key=lambda x: x.timestamp)
            
            # Verify each entry and chain links
            previous_hash = None
            for entry in sorted_entries:
                # Verify individual entry integrity
                if not self.verify_entry_integrity(entry):
                    return False
                
                # Verify chain link
                if entry.hash_chain_previous != previous_hash:
                    self.logger.warning(f"Hash chain break detected at entry: {entry.entry_id}")
                    return False
                
                previous_hash = entry.hash_chain_current
            
            self.logger.info(f"Verified integrity of {len(entries)} audit log entries")
            return True
            
        except Exception as e:
            self.logger.error(f"Chain integrity verification failed: {e}")
            return False
    
    def get_audit_trail(self, 
                       email_uid: Optional[str] = None,
                       account_id: Optional[str] = None,
                       component: Optional[str] = None,
                       start_time: Optional[datetime] = None,
                       end_time: Optional[datetime] = None) -> List[AuditLogEntry]:
        """
        Retrieve audit trail entries based on filters.
        
        Args:
            email_uid: Filter by email UID
            account_id: Filter by account ID
            component: Filter by component
            start_time: Filter by start time
            end_time: Filter by end time
            
        Returns:
            List of matching audit entries
        """
        if not self.database_manager:
            raise AuditError("Database manager not available for audit trail retrieval")
        
        return self.database_manager.get_audit_entries(
            email_uid=email_uid,
            account_id=account_id,
            component=component,
            start_time=start_time,
            end_time=end_time
        )
    
    def _load_or_create_signing_key(self) -> rsa.RSAPrivateKey:
        """Load existing signing key or create a new one."""
        if self.signing_key_path.exists():
            try:
                with open(self.signing_key_path, 'rb') as f:
                    private_key = serialization.load_pem_private_key(
                        f.read(),
                        password=None,
                        backend=default_backend()
                    )
                
                self.logger.info("Audit signing key loaded successfully")
                return private_key
                
            except Exception as e:
                self.logger.error(f"Failed to load signing key: {e}")
                raise AuditError(f"Failed to load signing key: {e}")
        else:
            # Generate new RSA key pair
            try:
                private_key = rsa.generate_private_key(
                    public_exponent=65537,
                    key_size=2048,
                    backend=default_backend()
                )
                
                # Ensure key directory exists
                self.signing_key_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Save private key
                with open(self.signing_key_path, 'wb') as f:
                    f.write(private_key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.PKCS8,
                        encryption_algorithm=serialization.NoEncryption()
                    ))
                
                # Set restrictive permissions
                self.signing_key_path.chmod(0o600)
                
                # Save public key for verification
                public_key_path = self.signing_key_path.with_suffix('.pub')
                with open(public_key_path, 'wb') as f:
                    f.write(private_key.public_key().public_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PublicFormat.SubjectPublicKeyInfo
                    ))
                
                self.logger.info("New audit signing key generated and stored securely")
                return private_key
                
            except Exception as e:
                self.logger.error(f"Failed to create signing key: {e}")
                raise AuditError(f"Failed to create signing key: {e}")
    
    def _calculate_entry_hash(self, entry: AuditLogEntry) -> str:
        """Calculate SHA-256 hash of audit entry for chain integrity."""
        try:
            # Create deterministic representation
            entry_dict = entry.to_dict()
            entry_json = json.dumps(entry_dict, sort_keys=True, separators=(',', ':'))
            
            # Calculate hash
            hash_obj = hashlib.new(self.hash_algorithm)
            hash_obj.update(entry_json.encode('utf-8'))
            
            return hash_obj.hexdigest()
            
        except Exception as e:
            raise AuditError(f"Failed to calculate entry hash: {e}")
    
    def _sign_entry(self, entry: AuditLogEntry) -> str:
        """Create RSA digital signature for audit entry."""
        try:
            # Create signature payload
            payload = f"{entry.entry_id}:{entry.timestamp.isoformat()}:{entry.hash_chain_current}"
            
            # Sign with RSA private key
            signature = self._private_key.sign(
                payload.encode('utf-8'),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            # Return base64-encoded signature
            import base64
            return base64.b64encode(signature).decode('utf-8')
            
        except Exception as e:
            raise AuditError(f"Failed to sign audit entry: {e}")
    
    def _verify_signature(self, entry: AuditLogEntry) -> bool:
        """Verify RSA digital signature of audit entry."""
        try:
            if not entry.digital_signature:
                return False
            
            # Reconstruct signature payload
            payload = f"{entry.entry_id}:{entry.timestamp.isoformat()}:{entry.hash_chain_current}"
            
            # Decode signature
            import base64
            signature = base64.b64decode(entry.digital_signature.encode('utf-8'))
            
            # Verify signature
            self._public_key.verify(
                signature,
                payload.encode('utf-8'),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            return True
            
        except Exception:
            return False