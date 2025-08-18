"""
Tests for the Email Security Validator.

This module contains comprehensive tests for government-grade security validation
including sender authorization, attachment scanning, content analysis, and
digital signature verification.
"""

import hashlib
import json
import tempfile
import unittest
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from src.email.security_validator import (
    EmailSecurityValidator,
    SecurityValidationResult,
    AttachmentScanResult,
    ContentAnalysisResult,
    DigitalSignatureResult,
    SecurityValidatorFactory
)
from src.security.exceptions import (
    EmailSecurityError,
    SenderAuthorizationError,
    AttachmentThreatError,
    ContentThreatError
)


class TestEmailSecurityValidator(unittest.TestCase):
    """Test cases for EmailSecurityValidator."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config = {
            'government_domains': ['dol.gov', 'labor.gov', 'test.gov'],
            'antivirus_engine': '/usr/bin/clamav',
            'max_attachment_size': 10 * 1024 * 1024,  # 10MB for testing
            'quarantine_directory': '/tmp/test_quarantine',
            'signature_verification_enabled': True,
            'trusted_ca_certificates': '/etc/ssl/certs'
        }
        
        self.validator = EmailSecurityValidator(self.test_config)
        
        # Create test email message
        self.test_email = EmailMessage()
        self.test_email['From'] = 'test@dol.gov'
        self.test_email['To'] = 'recipient@dol.gov'
        self.test_email['Subject'] = 'Test Email'
        self.test_email.set_content('This is a test email message.')
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up quarantine directory
        quarantine_path = Path('/tmp/test_quarantine')
        if quarantine_path.exists():
            for file in quarantine_path.glob('*'):
                file.unlink()
            quarantine_path.rmdir()
    
    def test_validator_initialization(self):
        """Test validator initialization with configuration."""
        self.assertEqual(self.validator.government_domains, {'dol.gov', 'labor.gov', 'test.gov'})
        self.assertEqual(self.validator.max_attachment_size, 10 * 1024 * 1024)
        self.assertTrue(self.validator.signature_verification_enabled)
        self.assertTrue(self.validator.quarantine_directory.exists())
    
    def test_sender_authorization_valid_government_domain(self):
        """Test sender authorization with valid government domain."""
        valid_senders = [
            'user@dol.gov',
            'admin@labor.gov',
            'test@subdomain.dol.gov',
            'official@test.gov'
        ]
        
        for sender in valid_senders:
            with self.subTest(sender=sender):
                result = self.validator._validate_sender_authorization(sender)
                self.assertTrue(result, f"Should authorize {sender}")
    
    def test_sender_authorization_invalid_domain(self):
        """Test sender authorization with invalid domains."""
        invalid_senders = [
            'user@gmail.com',
            'admin@company.com',
            'test@malicious.com',
            'phishing@fake-dol.gov.evil.com'
        ]
        
        for sender in invalid_senders:
            with self.subTest(sender=sender):
                result = self.validator._validate_sender_authorization(sender)
                self.assertFalse(result, f"Should not authorize {sender}")
    
    def test_sender_authorization_invalid_format(self):
        """Test sender authorization with invalid email formats."""
        invalid_formats = [
            'invalid-email',
            '@dol.gov',
            'user@',
            '',
            'user@domain@dol.gov'
        ]
        
        for sender in invalid_formats:
            with self.subTest(sender=sender):
                result = self.validator._validate_sender_authorization(sender)
                self.assertFalse(result, f"Should not authorize invalid format: {sender}")
    
    def test_content_analysis_safe_content(self):
        """Test content analysis with safe content."""
        safe_content = """
        Dear Colleague,
        
        Please review the attached quarterly report for your department.
        The meeting is scheduled for next Tuesday at 2 PM.
        
        Best regards,
        John Smith
        """
        
        result = self.validator._analyze_content_safety(safe_content)
        
        self.assertTrue(result.is_safe)
        self.assertFalse(result.phishing_detected)
        self.assertEqual(len(result.suspicious_links), 0)
        self.assertEqual(len(result.malicious_patterns), 0)
        self.assertGreaterEqual(result.confidence_score, 0.7)
    
    def test_content_analysis_phishing_content(self):
        """Test content analysis with phishing content."""
        phishing_content = """
        URGENT ACTION REQUIRED!
        
        Your account has been suspended. Click here immediately to verify your account now.
        Confirm your identity within 24 hours or lose access permanently.
        
        Click: http://fake-dol.gov.malicious.com/verify
        """
        
        result = self.validator._analyze_content_safety(phishing_content)
        
        self.assertFalse(result.is_safe)
        self.assertTrue(result.phishing_detected)
        self.assertGreater(len(result.suspicious_links), 0)
        self.assertLess(result.confidence_score, 0.7)
    
    def test_content_analysis_malicious_patterns(self):
        """Test content analysis with malicious patterns."""
        malicious_content = """
        <script>alert('XSS');</script>
        <a href="javascript:void(0)">Click here</a>
        <iframe src="data:text/html,<script>alert('XSS')</script>"></iframe>
        """
        
        result = self.validator._analyze_content_safety(malicious_content)
        
        self.assertFalse(result.is_safe)
        self.assertGreater(len(result.malicious_patterns), 0)
        self.assertLess(result.confidence_score, 0.7)
    
    def test_content_analysis_suspicious_links(self):
        """Test content analysis with suspicious links."""
        suspicious_content = """
        Please visit these links:
        http://192.168.1.1/malware
        https://bit.ly/suspicious
        http://malicious.tk/phishing
        """
        
        result = self.validator._analyze_content_safety(suspicious_content)
        
        self.assertFalse(result.is_safe)
        self.assertGreater(len(result.suspicious_links), 0)
    
    @patch('subprocess.run')
    def test_attachment_scanning_clean_file(self, mock_subprocess):
        """Test attachment scanning with clean file."""
        # Mock ClamAV returning clean result
        mock_subprocess.return_value = Mock(returncode=0, stdout='', stderr='')
        
        # Create email with attachment
        email_with_attachment = EmailMessage()
        email_with_attachment['From'] = 'test@dol.gov'
        email_with_attachment.set_content('Email with attachment')
        
        # Add clean text attachment
        attachment_content = b'This is a clean text file.'
        email_with_attachment.add_attachment(
            attachment_content,
            maintype='text',
            subtype='plain',
            filename='clean_file.txt'
        )
        
        results = self.validator._scan_attachments(email_with_attachment)
        
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].is_safe)
        self.assertFalse(results[0].threat_detected)
        self.assertEqual(results[0].filename, 'clean_file.txt')
        self.assertEqual(results[0].scan_engine, 'clamav')
    
    @patch('subprocess.run')
    def test_attachment_scanning_malicious_file(self, mock_subprocess):
        """Test attachment scanning with malicious file."""
        # Mock ClamAV returning threat detected
        mock_subprocess.return_value = Mock(
            returncode=1,
            stdout='test_file.exe: Trojan.Generic FOUND',
            stderr=''
        )
        
        # Create email with malicious attachment
        email_with_attachment = EmailMessage()
        email_with_attachment['From'] = 'test@dol.gov'
        email_with_attachment.set_content('Email with malicious attachment')
        
        # Add malicious attachment (simulated)
        malicious_content = b'MZ\x90\x00'  # PE header signature
        email_with_attachment.add_attachment(
            malicious_content,
            maintype='application',
            subtype='octet-stream',
            filename='malware.exe'
        )
        
        results = self.validator._scan_attachments(email_with_attachment)
        
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].is_safe)
        self.assertTrue(results[0].threat_detected)
        self.assertEqual(results[0].threat_type, 'Trojan.Generic')
        self.assertEqual(results[0].filename, 'malware.exe')
    
    def test_attachment_scanning_oversized_file(self):
        """Test attachment scanning with oversized file."""
        # Create email with oversized attachment
        email_with_attachment = EmailMessage()
        email_with_attachment['From'] = 'test@dol.gov'
        email_with_attachment.set_content('Email with oversized attachment')
        
        # Create oversized content (larger than 10MB limit)
        oversized_content = b'X' * (11 * 1024 * 1024)
        email_with_attachment.add_attachment(
            oversized_content,
            maintype='application',
            subtype='octet-stream',
            filename='large_file.bin'
        )
        
        results = self.validator._scan_attachments(email_with_attachment)
        
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].is_safe)
        self.assertTrue(results[0].threat_detected)
        self.assertEqual(results[0].threat_type, 'OVERSIZED_FILE')
        self.assertEqual(results[0].scan_engine, 'size_check')
    
    def test_basic_file_validation_dangerous_extensions(self):
        """Test basic file validation with dangerous extensions."""
        dangerous_files = [
            ('malware.exe', b'MZ\x90\x00'),
            ('script.bat', b'@echo off'),
            ('virus.scr', b'screensaver'),
            ('trojan.com', b'command')
        ]
        
        for filename, content in dangerous_files:
            with self.subTest(filename=filename):
                file_hash = hashlib.sha256(content).hexdigest()
                timestamp = datetime.utcnow()
                
                result = self.validator._basic_file_validation(
                    filename, content, file_hash, timestamp
                )
                
                self.assertFalse(result.is_safe)
                self.assertTrue(result.threat_detected)
                self.assertEqual(result.threat_type, 'DANGEROUS_FILE_TYPE')
    
    def test_basic_file_validation_executable_signatures(self):
        """Test basic file validation with executable signatures."""
        executable_signatures = [
            ('windows.exe', b'MZ\x90\x00\x03\x00\x00\x00'),  # PE header
            ('linux.bin', b'\x7fELF\x01\x01\x01\x00'),  # ELF header
            ('java.class', b'\xca\xfe\xba\xbe\x00\x00')  # Java class
        ]
        
        for filename, content in executable_signatures:
            with self.subTest(filename=filename):
                file_hash = hashlib.sha256(content).hexdigest()
                timestamp = datetime.utcnow()
                
                result = self.validator._basic_file_validation(
                    filename, content, file_hash, timestamp
                )
                
                self.assertFalse(result.is_safe)
                self.assertTrue(result.threat_detected)
    
    def test_digital_signature_verification_disabled(self):
        """Test digital signature verification when disabled."""
        # Create validator with signature verification disabled
        config = self.test_config.copy()
        config['signature_verification_enabled'] = False
        validator = EmailSecurityValidator(config)
        
        result = validator._verify_digital_signature(self.test_email)
        
        self.assertFalse(result.is_signed)
        self.assertTrue(result.signature_valid)  # Should pass when disabled
        self.assertIsNone(result.signer_certificate)
    
    def test_digital_signature_verification_no_signature(self):
        """Test digital signature verification with unsigned email."""
        result = self.validator._verify_digital_signature(self.test_email)
        
        self.assertFalse(result.is_signed)
        self.assertFalse(result.signature_valid)
        self.assertIsNone(result.signer_certificate)
    
    def test_threat_level_calculation_low(self):
        """Test threat level calculation for low threat."""
        content_analysis = ContentAnalysisResult(
            is_safe=True,
            phishing_detected=False,
            suspicious_links=[],
            malicious_patterns=[],
            confidence_score=0.9,
            analysis_timestamp=datetime.utcnow()
        )
        
        signature_result = DigitalSignatureResult(
            is_signed=False,
            signature_valid=True,
            signer_certificate=None,
            trust_chain_valid=False,
            signature_algorithm=None,
            verification_timestamp=datetime.utcnow()
        )
        
        threat_level = self.validator._calculate_threat_level(
            sender_authorized=True,
            content_analysis=content_analysis,
            attachments_safe=True,
            signature_result=signature_result
        )
        
        self.assertEqual(threat_level, 'LOW')
    
    def test_threat_level_calculation_critical(self):
        """Test threat level calculation for critical threat."""
        content_analysis = ContentAnalysisResult(
            is_safe=False,
            phishing_detected=True,
            suspicious_links=['http://malicious.com'],
            malicious_patterns=['<script>'],
            confidence_score=0.1,
            analysis_timestamp=datetime.utcnow()
        )
        
        signature_result = DigitalSignatureResult(
            is_signed=True,
            signature_valid=False,
            signer_certificate=None,
            trust_chain_valid=False,
            signature_algorithm=None,
            verification_timestamp=datetime.utcnow()
        )
        
        threat_level = self.validator._calculate_threat_level(
            sender_authorized=False,
            content_analysis=content_analysis,
            attachments_safe=False,
            signature_result=signature_result
        )
        
        self.assertEqual(threat_level, 'CRITICAL')
    
    @patch('src.email.security_validator.EmailSecurityValidator._alert_security_personnel')
    def test_quarantine_email(self, mock_alert):
        """Test email quarantine functionality."""
        # Create validation result requiring quarantine
        validation_result = SecurityValidationResult(
            is_valid=False,
            sender_authorized=False,
            content_safe=False,
            attachments_safe=True,
            digital_signature_valid=False,
            threat_level='HIGH',
            security_issues=['Unauthorized sender', 'Phishing detected'],
            quarantine_required=True,
            validation_timestamp=datetime.utcnow()
        )
        
        sender = 'malicious@evil.com'
        
        # Test quarantine
        self.validator._quarantine_email(self.test_email, sender, validation_result)
        
        # Verify quarantine files were created
        quarantine_files = list(self.validator.quarantine_directory.glob('quarantine_*.eml'))
        metadata_files = list(self.validator.quarantine_directory.glob('quarantine_*.json'))
        
        self.assertEqual(len(quarantine_files), 1)
        self.assertEqual(len(metadata_files), 1)
        
        # Verify metadata content
        with open(metadata_files[0], 'r') as f:
            metadata = json.load(f)
        
        self.assertEqual(metadata['sender'], sender)
        self.assertEqual(metadata['threat_level'], 'HIGH')
        self.assertIn('Unauthorized sender', metadata['security_issues'])
        
        # Verify security alert was called
        mock_alert.assert_called_once_with(sender, validation_result)
    
    @patch('src.email.security_validator.EmailSecurityValidator._scan_attachments')
    @patch('src.email.security_validator.EmailSecurityValidator._analyze_content_safety')
    @patch('src.email.security_validator.EmailSecurityValidator._verify_digital_signature')
    @patch('src.email.security_validator.EmailSecurityValidator._quarantine_email')
    def test_validate_email_security_comprehensive(self, mock_quarantine, mock_signature,
                                                  mock_content, mock_attachments):
        """Test comprehensive email security validation."""
        # Setup mocks
        mock_content.return_value = ContentAnalysisResult(
            is_safe=True,
            phishing_detected=False,
            suspicious_links=[],
            malicious_patterns=[],
            confidence_score=0.9,
            analysis_timestamp=datetime.utcnow()
        )
        
        mock_attachments.return_value = [
            AttachmentScanResult(
                filename='document.pdf',
                is_safe=True,
                threat_detected=False,
                threat_type=None,
                scan_engine='clamav',
                scan_timestamp=datetime.utcnow(),
                file_hash='abc123'
            )
        ]
        
        mock_signature.return_value = DigitalSignatureResult(
            is_signed=False,
            signature_valid=True,
            signer_certificate=None,
            trust_chain_valid=False,
            signature_algorithm=None,
            verification_timestamp=datetime.utcnow()
        )
        
        # Test validation
        sender = 'user@dol.gov'
        content = 'Safe email content'
        
        result = self.validator.validate_email_security(
            self.test_email, sender, content
        )
        
        # Verify results
        self.assertTrue(result.is_valid)
        self.assertTrue(result.sender_authorized)
        self.assertTrue(result.content_safe)
        self.assertTrue(result.attachments_safe)
        self.assertEqual(result.threat_level, 'LOW')
        self.assertFalse(result.quarantine_required)
        
        # Verify methods were called
        mock_content.assert_called_once_with(content)
        mock_attachments.assert_called_once_with(self.test_email)
        mock_signature.assert_called_once_with(self.test_email)
        mock_quarantine.assert_not_called()
    
    def test_validate_email_security_malicious_email(self):
        """Test validation of malicious email requiring quarantine."""
        # Create malicious email
        malicious_email = EmailMessage()
        malicious_email['From'] = 'attacker@evil.com'
        malicious_email['Subject'] = 'URGENT: Verify your account now!'
        malicious_email.set_content(
            'Click here immediately to verify your account: http://fake-dol.gov.evil.com'
        )
        
        sender = 'attacker@evil.com'
        content = malicious_email.get_content()
        
        with patch('src.email.security_validator.EmailSecurityValidator._quarantine_email') as mock_quarantine:
            result = self.validator.validate_email_security(
                malicious_email, sender, content
            )
            
            # Verify malicious email is caught
            self.assertFalse(result.is_valid)
            self.assertFalse(result.sender_authorized)
            self.assertFalse(result.content_safe)
            self.assertIn(result.threat_level, ['HIGH', 'CRITICAL'])
            self.assertTrue(result.quarantine_required)
            
            # Verify quarantine was called
            mock_quarantine.assert_called_once()


class TestSecurityValidatorFactory(unittest.TestCase):
    """Test cases for SecurityValidatorFactory."""
    
    def test_create_validator_with_config(self):
        """Test creating validator with custom configuration."""
        config = {
            'government_domains': ['custom.gov'],
            'max_attachment_size': 5 * 1024 * 1024
        }
        
        validator = SecurityValidatorFactory.create_validator(config)
        
        self.assertIsInstance(validator, EmailSecurityValidator)
        self.assertEqual(validator.government_domains, {'custom.gov'})
        self.assertEqual(validator.max_attachment_size, 5 * 1024 * 1024)
    
    def test_create_default_validator(self):
        """Test creating validator with default configuration."""
        validator = SecurityValidatorFactory.create_default_validator()
        
        self.assertIsInstance(validator, EmailSecurityValidator)
        self.assertIn('dol.gov', validator.government_domains)
        self.assertEqual(validator.max_attachment_size, 50 * 1024 * 1024)


class TestSecurityValidationIntegration(unittest.TestCase):
    """Integration tests for security validation with real scenarios."""
    
    def setUp(self):
        """Set up integration test fixtures."""
        # Create validator with signature verification disabled for testing
        config = {
            'government_domains': ['dol.gov', 'labor.gov', 'osha.gov', 'bls.gov'],
            'antivirus_engine': '/usr/bin/clamav',
            'max_attachment_size': 50 * 1024 * 1024,
            'quarantine_directory': '/tmp/test_quarantine',
            'signature_verification_enabled': False,  # Disabled for testing
            'trusted_ca_certificates': '/etc/ssl/certs'
        }
        self.validator = SecurityValidatorFactory.create_validator(config)
    
    def test_executive_order_email_validation(self):
        """Test validation of legitimate Executive Order email."""
        # Create legitimate EO email
        eo_email = EmailMessage()
        eo_email['From'] = 'executive.orders@dol.gov'
        eo_email['To'] = 'processing@dol.gov'
        eo_email['Subject'] = 'Executive Order 14001 - Implementation Required'
        eo_email.set_content("""
        Dear Implementation Team,
        
        Please find attached Executive Order 14001 requiring immediate implementation.
        This order addresses workplace safety standards and must be processed within 30 days.
        
        Please confirm receipt and provide implementation timeline.
        
        Best regards,
        Executive Orders Office
        U.S. Department of Labor
        """)
        
        # Add PDF attachment (simulated)
        pdf_content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj'
        eo_email.add_attachment(
            pdf_content,
            maintype='application',
            subtype='pdf',
            filename='EO_14001.pdf'
        )
        
        sender = 'executive.orders@dol.gov'
        # Get text content from multipart message
        content = ""
        for part in eo_email.walk():
            if part.get_content_type() == 'text/plain':
                content = part.get_content()
                break
        
        with patch('subprocess.run') as mock_subprocess:
            # Mock clean antivirus scan
            mock_subprocess.return_value = Mock(returncode=0, stdout='', stderr='')
            
            result = self.validator.validate_email_security(eo_email, sender, content)
            
            # Should pass all validations
            self.assertTrue(result.is_valid)
            self.assertTrue(result.sender_authorized)
            self.assertTrue(result.content_safe)
            self.assertTrue(result.attachments_safe)
            self.assertEqual(result.threat_level, 'LOW')
            self.assertFalse(result.quarantine_required)
    
    def test_phishing_attack_detection(self):
        """Test detection of sophisticated phishing attack."""
        # Create sophisticated phishing email
        phishing_email = EmailMessage()
        phishing_email['From'] = 'security@do1.gov'  # Typosquatting
        phishing_email['To'] = 'employee@dol.gov'
        phishing_email['Subject'] = 'URGENT: Security Verification Required'
        phishing_email.set_content("""
        Dear Employee,
        
        Our security systems have detected suspicious activity on your account.
        URGENT ACTION REQUIRED to prevent account suspension.
        
        Click here immediately to verify your account:
        https://dol-security-verification.tk/verify?token=abc123
        
        You must confirm your identity within 2 hours or your access will be permanently disabled.
        
        Department of Labor Security Team
        """)
        
        sender = 'security@do1.gov'  # Typosquatting domain
        content = phishing_email.get_content()
        
        result = self.validator.validate_email_security(phishing_email, sender, content)
        
        # Should detect as malicious
        self.assertFalse(result.is_valid)
        self.assertFalse(result.sender_authorized)  # Typosquatting domain
        self.assertFalse(result.content_safe)  # Phishing patterns
        self.assertIn(result.threat_level, ['HIGH', 'CRITICAL'])
        self.assertTrue(result.quarantine_required)
        self.assertTrue(any('Unauthorized sender' in issue for issue in result.security_issues))
    
    def test_malware_attachment_detection(self):
        """Test detection of malware in email attachments."""
        # Create email with malware attachment
        malware_email = EmailMessage()
        malware_email['From'] = 'partner@dol.gov'
        malware_email['To'] = 'employee@dol.gov'
        malware_email['Subject'] = 'Updated Software Package'
        malware_email.set_content("""
        Please install the updated software package attached to this email.
        This update includes important security patches.
        """)
        
        # Add malicious executable (simulated)
        malware_content = b'MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff'  # PE header
        malware_email.add_attachment(
            malware_content,
            maintype='application',
            subtype='octet-stream',
            filename='security_update.exe'
        )
        
        sender = 'partner@dol.gov'
        # Get text content from multipart message
        content = ""
        for part in malware_email.walk():
            if part.get_content_type() == 'text/plain':
                content = part.get_content()
                break
        
        with patch('subprocess.run') as mock_subprocess:
            # Mock malware detection
            mock_subprocess.return_value = Mock(
                returncode=1,
                stdout='security_update.exe: Trojan.Win32.Generic FOUND',
                stderr=''
            )
            
            result = self.validator.validate_email_security(malware_email, sender, content)
            
            # Should detect malware
            self.assertFalse(result.is_valid)
            self.assertTrue(result.sender_authorized)  # Valid sender
            self.assertTrue(result.content_safe)  # Safe content
            self.assertFalse(result.attachments_safe)  # Malicious attachment
            self.assertIn(result.threat_level, ['MEDIUM', 'HIGH', 'CRITICAL'])
            self.assertTrue(result.quarantine_required)


if __name__ == '__main__':
    unittest.main()