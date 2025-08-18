"""
Government-Grade Security Validator for Email Processing

This module implements federal-grade security validation for email content,
including sender authorization, attachment scanning, content safety analysis,
and digital signature verification.
"""

import hashlib
import logging
import re
import subprocess
import tempfile
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union
from datetime import datetime, timedelta
import email.utils
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.exceptions import InvalidSignature

from ..security.exceptions import SecurityError, ValidationError


logger = logging.getLogger(__name__)


@dataclass
class SecurityValidationResult:
    """Result of security validation for an email."""
    is_valid: bool
    sender_authorized: bool
    content_safe: bool
    attachments_safe: bool
    digital_signature_valid: bool
    threat_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    security_issues: List[str]
    quarantine_required: bool
    validation_timestamp: datetime


@dataclass
class AttachmentScanResult:
    """Result of attachment security scanning."""
    filename: str
    is_safe: bool
    threat_detected: bool
    threat_type: Optional[str]
    scan_engine: str
    scan_timestamp: datetime
    file_hash: str


@dataclass
class ContentAnalysisResult:
    """Result of content safety analysis."""
    is_safe: bool
    phishing_detected: bool
    suspicious_links: List[str]
    malicious_patterns: List[str]
    confidence_score: float
    analysis_timestamp: datetime


@dataclass
class DigitalSignatureResult:
    """Result of digital signature verification."""
    is_signed: bool
    signature_valid: bool
    signer_certificate: Optional[str]
    trust_chain_valid: bool
    signature_algorithm: Optional[str]
    verification_timestamp: datetime


class EmailSecurityValidator:
    """
    Government-grade security validator for email processing.
    
    Implements comprehensive security validation including:
    - Sender authorization against government domain whitelist
    - Attachment security scanning with government-approved antivirus
    - Content safety analysis and threat detection
    - Digital signature verification for authenticated emails
    """
    
    def __init__(self, config: Dict[str, any]):
        """
        Initialize the security validator.
        
        Args:
            config: Configuration dictionary containing:
                - government_domains: List of authorized government domains
                - antivirus_engine: Path to antivirus scanning engine
                - max_attachment_size: Maximum allowed attachment size in bytes
                - quarantine_directory: Directory for quarantined files
                - signature_verification_enabled: Enable digital signature verification
                - trusted_ca_certificates: Path to trusted CA certificates
        """
        self.config = config
        self.government_domains = set(config.get('government_domains', [
            'dol.gov', 'labor.gov', 'osha.gov', 'bls.gov', 'dol.state.gov'
        ]))
        self.antivirus_engine = config.get('antivirus_engine', '/usr/bin/clamav')
        self.max_attachment_size = config.get('max_attachment_size', 50 * 1024 * 1024)  # 50MB
        self.quarantine_directory = Path(config.get('quarantine_directory', '/tmp/quarantine'))
        self.signature_verification_enabled = config.get('signature_verification_enabled', True)
        self.trusted_ca_path = config.get('trusted_ca_certificates', '/etc/ssl/certs')
        
        # Ensure quarantine directory exists
        self.quarantine_directory.mkdir(parents=True, exist_ok=True)
        
        # Compile suspicious patterns for content analysis
        self._compile_threat_patterns()
        
        logger.info("EmailSecurityValidator initialized with government-grade security controls")
    
    def _compile_threat_patterns(self):
        """Compile regex patterns for threat detection."""
        self.phishing_patterns = [
            re.compile(r'click\s+here\s+immediately', re.IGNORECASE),
            re.compile(r'verify\s+your\s+account\s+now', re.IGNORECASE),
            re.compile(r'suspended\s+account', re.IGNORECASE),
            re.compile(r'urgent\s+action\s+required', re.IGNORECASE),
            re.compile(r'confirm\s+your\s+identity', re.IGNORECASE),
        ]
        
        self.suspicious_link_patterns = [
            re.compile(r'https?://[^/\s]*\.tk[/\s]', re.IGNORECASE),  # Suspicious TLD
            re.compile(r'https?://[^/\s]*\.ml[/\s]', re.IGNORECASE),  # Suspicious TLD
            re.compile(r'https?://\d+\.\d+\.\d+\.\d+[/\s]', re.IGNORECASE),  # IP addresses
            re.compile(r'https?://[^/\s]*(?:bit\.ly|tinyurl|t\.co)[/\s]', re.IGNORECASE),  # URL shorteners
            re.compile(r'https?://[^/\s]*malicious[^/\s]*[/\s]', re.IGNORECASE),  # Malicious domains
        ]
        
        self.malicious_patterns = [
            re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL),
            re.compile(r'javascript:', re.IGNORECASE),
            re.compile(r'vbscript:', re.IGNORECASE),
            re.compile(r'data:text/html', re.IGNORECASE),
        ]
    
    def validate_email_security(self, email_message: EmailMessage, 
                              sender: str, content: str) -> SecurityValidationResult:
        """
        Perform comprehensive security validation on an email.
        
        Args:
            email_message: The email message object
            sender: Email sender address
            content: Email content text
            
        Returns:
            SecurityValidationResult with validation details
        """
        logger.info(f"Starting security validation for email from {sender}")
        
        validation_start = datetime.utcnow()
        security_issues = []
        
        # 1. Validate sender authorization
        sender_authorized = self._validate_sender_authorization(sender)
        if not sender_authorized:
            security_issues.append(f"Unauthorized sender domain: {sender}")
        
        # 2. Analyze content safety
        content_analysis = self._analyze_content_safety(content)
        if not content_analysis.is_safe:
            security_issues.extend([
                f"Phishing detected: {content_analysis.phishing_detected}",
                f"Suspicious links: {len(content_analysis.suspicious_links)}",
                f"Malicious patterns: {len(content_analysis.malicious_patterns)}"
            ])
        
        # 3. Scan attachments
        attachment_results = self._scan_attachments(email_message)
        attachments_safe = all(result.is_safe for result in attachment_results)
        if not attachments_safe:
            threat_attachments = [r.filename for r in attachment_results if not r.is_safe]
            security_issues.append(f"Malicious attachments detected: {threat_attachments}")
        
        # 4. Verify digital signature
        signature_result = self._verify_digital_signature(email_message)
        if self.signature_verification_enabled and not signature_result.signature_valid:
            security_issues.append("Digital signature verification failed")
        
        # Determine overall threat level
        threat_level = self._calculate_threat_level(
            sender_authorized, content_analysis, attachments_safe, signature_result
        )
        
        # Determine if quarantine is required
        quarantine_required = (
            threat_level in ['HIGH', 'CRITICAL'] or
            not attachments_safe or
            content_analysis.phishing_detected
        )
        
        is_valid = (
            sender_authorized and
            content_analysis.is_safe and
            attachments_safe and
            (signature_result.signature_valid if self.signature_verification_enabled else True)
        )
        
        result = SecurityValidationResult(
            is_valid=is_valid,
            sender_authorized=sender_authorized,
            content_safe=content_analysis.is_safe,
            attachments_safe=attachments_safe,
            digital_signature_valid=signature_result.signature_valid,
            threat_level=threat_level,
            security_issues=security_issues,
            quarantine_required=quarantine_required,
            validation_timestamp=validation_start
        )
        
        if quarantine_required:
            self._quarantine_email(email_message, sender, result)
        
        logger.info(f"Security validation completed for {sender}: "
                   f"valid={is_valid}, threat_level={threat_level}")
        
        return result
    
    def _validate_sender_authorization(self, sender: str) -> bool:
        """
        Validate sender authorization against government domain whitelist.
        
        Args:
            sender: Email sender address
            
        Returns:
            True if sender is authorized, False otherwise
        """
        try:
            # Extract domain from sender email
            if '@' not in sender or sender.count('@') != 1:
                logger.warning(f"Invalid sender format: {sender}")
                return False
            
            # Check for empty parts
            parts = sender.split('@')
            if not parts[0] or not parts[1]:
                logger.warning(f"Invalid sender format: {sender}")
                return False
            
            domain = parts[1].lower()
            
            # Check against government domain whitelist
            is_authorized = any(
                domain == gov_domain or domain.endswith(f'.{gov_domain}')
                for gov_domain in self.government_domains
            )
            
            logger.debug(f"Sender authorization check for {sender}: {is_authorized}")
            return is_authorized
            
        except Exception as e:
            logger.error(f"Error validating sender authorization for {sender}: {e}")
            return False
    
    def _analyze_content_safety(self, content: str) -> ContentAnalysisResult:
        """
        Analyze email content for safety threats.
        
        Args:
            content: Email content text
            
        Returns:
            ContentAnalysisResult with analysis details
        """
        analysis_start = datetime.utcnow()
        
        # Check for phishing patterns
        phishing_detected = any(
            pattern.search(content) for pattern in self.phishing_patterns
        )
        
        # Extract and analyze suspicious links
        suspicious_links = []
        for pattern in self.suspicious_link_patterns:
            matches = pattern.findall(content)
            suspicious_links.extend(matches)
        
        # Check for malicious patterns
        malicious_patterns = []
        for pattern in self.malicious_patterns:
            matches = pattern.findall(content)
            malicious_patterns.extend(matches)
        
        # Calculate confidence score
        threat_indicators = (
            len([p for p in self.phishing_patterns if p.search(content)]) +
            len(suspicious_links) +
            len(malicious_patterns)
        )
        
        confidence_score = max(0.0, 1.0 - (threat_indicators * 0.2))
        is_safe = confidence_score >= 0.7 and not phishing_detected
        
        return ContentAnalysisResult(
            is_safe=is_safe,
            phishing_detected=phishing_detected,
            suspicious_links=suspicious_links,
            malicious_patterns=malicious_patterns,
            confidence_score=confidence_score,
            analysis_timestamp=analysis_start
        )
    
    def _scan_attachments(self, email_message: EmailMessage) -> List[AttachmentScanResult]:
        """
        Scan email attachments for malware and threats.
        
        Args:
            email_message: Email message with attachments
            
        Returns:
            List of AttachmentScanResult for each attachment
        """
        results = []
        
        for part in email_message.walk():
            if part.get_content_disposition() == 'attachment':
                filename = part.get_filename()
                if not filename:
                    continue
                
                try:
                    # Get attachment content
                    content = part.get_payload(decode=True)
                    if not content:
                        continue
                    
                    # Check file size
                    if len(content) > self.max_attachment_size:
                        logger.warning(f"Attachment {filename} exceeds size limit")
                        results.append(AttachmentScanResult(
                            filename=filename,
                            is_safe=False,
                            threat_detected=True,
                            threat_type="OVERSIZED_FILE",
                            scan_engine="size_check",
                            scan_timestamp=datetime.utcnow(),
                            file_hash=hashlib.sha256(content).hexdigest()
                        ))
                        continue
                    
                    # Perform antivirus scan
                    scan_result = self._scan_file_content(filename, content)
                    results.append(scan_result)
                    
                except Exception as e:
                    logger.error(f"Error scanning attachment {filename}: {e}")
                    results.append(AttachmentScanResult(
                        filename=filename,
                        is_safe=False,
                        threat_detected=True,
                        threat_type="SCAN_ERROR",
                        scan_engine="error",
                        scan_timestamp=datetime.utcnow(),
                        file_hash="unknown"
                    ))
        
        return results
    
    def _scan_file_content(self, filename: str, content: bytes) -> AttachmentScanResult:
        """
        Scan file content using antivirus engine.
        
        Args:
            filename: Name of the file
            content: File content bytes
            
        Returns:
            AttachmentScanResult with scan details
        """
        file_hash = hashlib.sha256(content).hexdigest()
        scan_timestamp = datetime.utcnow()
        
        try:
            # Create temporary file for scanning
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename}") as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name
            
            try:
                # Run antivirus scan (using ClamAV as example)
                result = subprocess.run([
                    'clamscan', '--no-summary', '--infected', temp_file_path
                ], capture_output=True, text=True, timeout=30)
                
                threat_detected = result.returncode != 0
                threat_type = None
                
                if threat_detected and result.stdout:
                    # Extract threat type from ClamAV output
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        if 'FOUND' in line:
                            threat_type = line.split(':')[1].strip().replace(' FOUND', '')
                            break
                
                return AttachmentScanResult(
                    filename=filename,
                    is_safe=not threat_detected,
                    threat_detected=threat_detected,
                    threat_type=threat_type,
                    scan_engine="clamav",
                    scan_timestamp=scan_timestamp,
                    file_hash=file_hash
                )
                
            finally:
                # Clean up temporary file
                Path(temp_file_path).unlink(missing_ok=True)
                
        except subprocess.TimeoutExpired:
            logger.error(f"Antivirus scan timeout for {filename}")
            return AttachmentScanResult(
                filename=filename,
                is_safe=False,
                threat_detected=True,
                threat_type="SCAN_TIMEOUT",
                scan_engine="clamav",
                scan_timestamp=scan_timestamp,
                file_hash=file_hash
            )
        except Exception as e:
            logger.error(f"Error during antivirus scan for {filename}: {e}")
            # Fallback to basic file type validation
            return self._basic_file_validation(filename, content, file_hash, scan_timestamp)
    
    def _basic_file_validation(self, filename: str, content: bytes, 
                             file_hash: str, scan_timestamp: datetime) -> AttachmentScanResult:
        """
        Perform basic file validation when antivirus is unavailable.
        
        Args:
            filename: Name of the file
            content: File content bytes
            file_hash: SHA256 hash of the file
            scan_timestamp: Timestamp of the scan
            
        Returns:
            AttachmentScanResult with basic validation
        """
        # Check for dangerous file extensions
        dangerous_extensions = {
            '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js',
            '.jar', '.app', '.deb', '.pkg', '.dmg', '.msi'
        }
        
        file_ext = Path(filename).suffix.lower()
        threat_detected = file_ext in dangerous_extensions
        
        # Check for executable signatures
        if not threat_detected and len(content) > 2:
            # Check for common executable signatures
            if content[:2] == b'MZ':  # Windows PE
                threat_detected = True
            elif content[:4] == b'\x7fELF':  # Linux ELF
                threat_detected = True
            elif content[:4] == b'\xca\xfe\xba\xbe':  # Java class
                threat_detected = True
        
        return AttachmentScanResult(
            filename=filename,
            is_safe=not threat_detected,
            threat_detected=threat_detected,
            threat_type="DANGEROUS_FILE_TYPE" if threat_detected else None,
            scan_engine="basic_validation",
            scan_timestamp=scan_timestamp,
            file_hash=file_hash
        )
    
    def _verify_digital_signature(self, email_message: EmailMessage) -> DigitalSignatureResult:
        """
        Verify digital signature of the email.
        
        Args:
            email_message: Email message to verify
            
        Returns:
            DigitalSignatureResult with verification details
        """
        verification_timestamp = datetime.utcnow()
        
        if not self.signature_verification_enabled:
            return DigitalSignatureResult(
                is_signed=False,
                signature_valid=True,  # Skip verification if disabled
                signer_certificate=None,
                trust_chain_valid=False,
                signature_algorithm=None,
                verification_timestamp=verification_timestamp
            )
        
        try:
            # Check for S/MIME signature
            content_type = email_message.get_content_type()
            
            if content_type == 'application/pkcs7-mime':
                # Handle S/MIME signed message
                return self._verify_smime_signature(email_message, verification_timestamp)
            elif content_type == 'multipart/signed':
                # Handle multipart signed message
                return self._verify_multipart_signature(email_message, verification_timestamp)
            else:
                # No signature found
                return DigitalSignatureResult(
                    is_signed=False,
                    signature_valid=False,
                    signer_certificate=None,
                    trust_chain_valid=False,
                    signature_algorithm=None,
                    verification_timestamp=verification_timestamp
                )
                
        except Exception as e:
            logger.error(f"Error verifying digital signature: {e}")
            return DigitalSignatureResult(
                is_signed=True,
                signature_valid=False,
                signer_certificate=None,
                trust_chain_valid=False,
                signature_algorithm=None,
                verification_timestamp=verification_timestamp
            )
    
    def _verify_smime_signature(self, email_message: EmailMessage, 
                               verification_timestamp: datetime) -> DigitalSignatureResult:
        """Verify S/MIME signature."""
        # Placeholder for S/MIME verification
        # In a real implementation, this would use cryptography library
        # to verify the PKCS#7 signature
        logger.info("S/MIME signature verification not fully implemented")
        
        return DigitalSignatureResult(
            is_signed=True,
            signature_valid=False,  # Conservative approach
            signer_certificate=None,
            trust_chain_valid=False,
            signature_algorithm="S/MIME",
            verification_timestamp=verification_timestamp
        )
    
    def _verify_multipart_signature(self, email_message: EmailMessage,
                                   verification_timestamp: datetime) -> DigitalSignatureResult:
        """Verify multipart signed message."""
        # Placeholder for multipart signature verification
        logger.info("Multipart signature verification not fully implemented")
        
        return DigitalSignatureResult(
            is_signed=True,
            signature_valid=False,  # Conservative approach
            signer_certificate=None,
            trust_chain_valid=False,
            signature_algorithm="PGP/MIME",
            verification_timestamp=verification_timestamp
        )
    
    def _calculate_threat_level(self, sender_authorized: bool, 
                               content_analysis: ContentAnalysisResult,
                               attachments_safe: bool,
                               signature_result: DigitalSignatureResult) -> str:
        """
        Calculate overall threat level based on validation results.
        
        Args:
            sender_authorized: Whether sender is authorized
            content_analysis: Content analysis result
            attachments_safe: Whether attachments are safe
            signature_result: Digital signature verification result
            
        Returns:
            Threat level: LOW, MEDIUM, HIGH, or CRITICAL
        """
        threat_score = 0
        
        # Sender authorization (high weight)
        if not sender_authorized:
            threat_score += 40
        
        # Content safety
        if content_analysis.phishing_detected:
            threat_score += 30
        if len(content_analysis.suspicious_links) > 0:
            threat_score += 20
        if len(content_analysis.malicious_patterns) > 0:
            threat_score += 25
        
        # Attachment safety (high weight)
        if not attachments_safe:
            threat_score += 35
        
        # Digital signature (medium weight)
        if self.signature_verification_enabled and not signature_result.signature_valid:
            threat_score += 15
        
        # Determine threat level
        if threat_score >= 70:
            return "CRITICAL"
        elif threat_score >= 50:
            return "HIGH"
        elif threat_score >= 25:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _quarantine_email(self, email_message: EmailMessage, sender: str,
                         validation_result: SecurityValidationResult):
        """
        Quarantine suspicious email for security review.
        
        Args:
            email_message: Email message to quarantine
            sender: Email sender
            validation_result: Security validation result
        """
        try:
            # Create quarantine filename with timestamp
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            sender_safe = re.sub(r'[^\w\-_.]', '_', sender)
            quarantine_filename = f"quarantine_{timestamp}_{sender_safe}.eml"
            quarantine_path = self.quarantine_directory / quarantine_filename
            
            # Save email to quarantine
            with open(quarantine_path, 'w', encoding='utf-8') as f:
                f.write(str(email_message))
            
            # Create metadata file
            metadata_path = quarantine_path.with_suffix('.json')
            metadata = {
                'sender': sender,
                'quarantine_timestamp': timestamp,
                'threat_level': validation_result.threat_level,
                'security_issues': validation_result.security_issues,
                'validation_result': {
                    'sender_authorized': validation_result.sender_authorized,
                    'content_safe': validation_result.content_safe,
                    'attachments_safe': validation_result.attachments_safe,
                    'digital_signature_valid': validation_result.digital_signature_valid
                }
            }
            
            import json
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.warning(f"Email from {sender} quarantined: {quarantine_filename}")
            
            # Alert security personnel (placeholder)
            self._alert_security_personnel(sender, validation_result)
            
        except Exception as e:
            logger.error(f"Error quarantining email from {sender}: {e}")
    
    def _alert_security_personnel(self, sender: str, 
                                 validation_result: SecurityValidationResult):
        """
        Alert security personnel about quarantined email.
        
        Args:
            sender: Email sender
            validation_result: Security validation result
        """
        # Placeholder for security alerting system
        # In a real implementation, this would integrate with:
        # - SIEM systems
        # - Security incident management
        # - Email notifications to security team
        # - Dashboard alerts
        
        logger.critical(f"SECURITY ALERT: Suspicious email from {sender} "
                       f"quarantined with threat level {validation_result.threat_level}")
        
        # Log security incident for audit trail
        logger.info(f"Security incident logged: sender={sender}, "
                   f"issues={validation_result.security_issues}")


class SecurityValidatorFactory:
    """Factory for creating security validator instances."""
    
    @staticmethod
    def create_validator(config: Dict[str, any]) -> EmailSecurityValidator:
        """
        Create a security validator instance.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            EmailSecurityValidator instance
        """
        return EmailSecurityValidator(config)
    
    @staticmethod
    def create_default_validator() -> EmailSecurityValidator:
        """
        Create a security validator with default configuration.
        
        Returns:
            EmailSecurityValidator with default settings
        """
        default_config = {
            'government_domains': [
                'dol.gov', 'labor.gov', 'osha.gov', 'bls.gov', 'dol.state.gov'
            ],
            'antivirus_engine': '/usr/bin/clamav',
            'max_attachment_size': 50 * 1024 * 1024,  # 50MB
            'quarantine_directory': '/tmp/quarantine',
            'signature_verification_enabled': True,
            'trusted_ca_certificates': '/etc/ssl/certs'
        }
        
        return EmailSecurityValidator(default_config)