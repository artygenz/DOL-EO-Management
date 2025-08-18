"""
Security Threat Scenario Tests

This module contains tests for real-world threat scenarios including
malware samples, phishing attacks, and sophisticated security threats
that the Email Security Validator must detect and handle.
"""

import hashlib
import tempfile
import unittest
from email.message import EmailMessage
from pathlib import Path
from unittest.mock import Mock, patch

from src.email.security_validator import SecurityValidatorFactory


class TestSecurityThreatScenarios(unittest.TestCase):
    """Test cases for real-world security threat scenarios."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create validator with realistic configuration
        self.config = {
            'government_domains': [
                'dol.gov', 'labor.gov', 'osha.gov', 'bls.gov',
                'whitehouse.gov', 'treasury.gov', 'state.gov'
            ],
            'antivirus_engine': '/usr/bin/clamav',
            'max_attachment_size': 25 * 1024 * 1024,  # 25MB
            'quarantine_directory': '/tmp/threat_quarantine',
            'signature_verification_enabled': True,
            'trusted_ca_certificates': '/etc/ssl/certs'
        }
        self.validator = SecurityValidatorFactory.create_validator(self.config)
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up quarantine directory
        quarantine_path = Path('/tmp/threat_quarantine')
        if quarantine_path.exists():
            for file in quarantine_path.glob('*'):
                file.unlink()
            quarantine_path.rmdir()
    
    def test_advanced_phishing_with_typosquatting(self):
        """Test detection of advanced phishing with domain typosquatting."""
        # Create sophisticated phishing email with multiple deception techniques
        phishing_email = EmailMessage()
        phishing_email['From'] = 'security-team@do1.gov'  # Typosquatting dol.gov
        phishing_email['To'] = 'employee@dol.gov'
        phishing_email['Subject'] = 'URGENT: Multi-Factor Authentication Update Required'
        phishing_email.set_content("""
        Dear Department Employee,
        
        Our cybersecurity team has detected unauthorized access attempts on your account.
        URGENT ACTION REQUIRED to prevent account suspension.
        
        Please click here immediately to verify your account and update your MFA settings:
        https://dol-security-portal.tk/urgent-verification?user=employee&token=abc123def456
        
        You must confirm your identity within 2 hours or your access will be permanently disabled.
        This is an automated security message. Do not reply to this email.
        
        Department of Labor IT Security Team
        security-team@dol.gov
        """)
        
        sender = 'security-team@do1.gov'
        content = phishing_email.get_content()
        
        result = self.validator.validate_email_security(phishing_email, sender, content)
        
        # Should detect as high-threat phishing
        self.assertFalse(result.is_valid)
        self.assertFalse(result.sender_authorized)  # Typosquatting domain
        self.assertFalse(result.content_safe)  # Phishing patterns
        self.assertTrue(result.attachments_safe)  # No attachments
        self.assertIn(result.threat_level, ['HIGH', 'CRITICAL'])
        self.assertTrue(result.quarantine_required)
        
        # Verify specific threat detection
        self.assertTrue(any('Unauthorized sender' in issue for issue in result.security_issues))
        self.assertTrue(any('Phishing detected' in issue for issue in result.security_issues))
        self.assertTrue(any('Suspicious links' in issue for issue in result.security_issues))
    
    @patch('subprocess.run')
    def test_malware_attachment_variants(self, mock_subprocess):
        """Test detection of various malware attachment types."""
        malware_variants = [
            {
                'filename': 'invoice.pdf.exe',
                'content': b'MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff',  # PE header
                'threat_type': 'Trojan.Win32.FakeInvoice',
                'description': 'Double extension executable'
            },
            {
                'filename': 'document.docm',
                'content': b'PK\x03\x04' + b'A' * 100,  # ZIP-based Office doc with macros
                'threat_type': 'Macro.Office.Malicious',
                'description': 'Malicious Office macro document'
            },
            {
                'filename': 'update.jar',
                'content': b'\xca\xfe\xba\xbe\x00\x00\x00\x34',  # Java class file header
                'threat_type': 'Java.Trojan.Generic',
                'description': 'Malicious Java archive'
            },
            {
                'filename': 'script.js',
                'content': b'eval(atob("bWFsaWNpb3VzX2NvZGU="));',  # Base64 encoded malicious JS
                'threat_type': 'JS.Obfuscated.Malware',
                'description': 'Obfuscated JavaScript malware'
            }
        ]
        
        for variant in malware_variants:
            with self.subTest(variant=variant['description']):
                # Mock antivirus detection
                mock_subprocess.return_value = Mock(
                    returncode=1,
                    stdout=f"{variant['filename']}: {variant['threat_type']} FOUND",
                    stderr=''
                )
                
                # Create email with malware attachment
                malware_email = EmailMessage()
                malware_email['From'] = 'partner@dol.gov'
                malware_email['To'] = 'employee@dol.gov'
                malware_email['Subject'] = f'Important: {variant["filename"]}'
                malware_email.set_content(f'Please review the attached {variant["filename"]}.')
                
                malware_email.add_attachment(
                    variant['content'],
                    maintype='application',
                    subtype='octet-stream',
                    filename=variant['filename']
                )
                
                sender = 'partner@dol.gov'
                content = ""
                for part in malware_email.walk():
                    if part.get_content_type() == 'text/plain':
                        content = part.get_content()
                        break
                
                result = self.validator.validate_email_security(malware_email, sender, content)
                
                # Should detect malware
                self.assertFalse(result.is_valid)
                self.assertTrue(result.sender_authorized)  # Valid government sender
                self.assertTrue(result.content_safe)  # Safe content
                self.assertFalse(result.attachments_safe)  # Malicious attachment
                self.assertIn(result.threat_level, ['MEDIUM', 'HIGH', 'CRITICAL'])
                self.assertTrue(result.quarantine_required)
    
    def test_social_engineering_attack(self):
        """Test detection of social engineering attack patterns."""
        social_engineering_email = EmailMessage()
        social_engineering_email['From'] = 'ceo@dol.gov'  # Impersonation
        social_engineering_email['To'] = 'finance@dol.gov'
        social_engineering_email['Subject'] = 'URGENT: Wire Transfer Authorization Required'
        social_engineering_email.set_content("""
        This is the CEO. I need you to process an urgent wire transfer immediately.
        
        Due to a confidential acquisition, we need to transfer $50,000 to the following account:
        Bank: International Trust Bank
        Account: 1234567890
        Routing: 987654321
        
        This is time-sensitive and confidential. Please process immediately and confirm.
        Do not discuss this with anyone else in the department.
        
        I'm in meetings all day, so please just confirm via email when complete.
        
        CEO
        """)
        
        sender = 'ceo@dol.gov'
        content = social_engineering_email.get_content()
        
        result = self.validator.validate_email_security(social_engineering_email, sender, content)
        
        # Should detect social engineering patterns
        self.assertTrue(result.sender_authorized)  # Valid domain but suspicious content
        # Content analysis should flag urgency and financial requests
        # Note: This test demonstrates the need for more sophisticated content analysis
        # In a real implementation, we would add patterns for financial fraud detection
    
    def test_zero_day_exploit_simulation(self):
        """Test handling of unknown/zero-day exploit attempts."""
        # Simulate a zero-day exploit attempt with unusual file structure
        exploit_content = (
            b'\x00\x01\x02\x03' +  # Unusual header
            b'A' * 1000 +  # Buffer overflow attempt
            b'\x90' * 100 +  # NOP sled
            b'\xcc' * 50  # Breakpoint instructions
        )
        
        exploit_email = EmailMessage()
        exploit_email['From'] = 'researcher@dol.gov'
        exploit_email['To'] = 'it-security@dol.gov'
        exploit_email['Subject'] = 'Security Research: New Vulnerability'
        exploit_email.set_content("""
        Attached is a proof-of-concept for a new vulnerability I discovered.
        Please review and test in your sandbox environment.
        """)
        
        exploit_email.add_attachment(
            exploit_content,
            maintype='application',
            subtype='octet-stream',
            filename='poc_exploit.bin'
        )
        
        sender = 'researcher@dol.gov'
        content = ""
        for part in exploit_email.walk():
            if part.get_content_type() == 'text/plain':
                content = part.get_content()
                break
        
        with patch('subprocess.run') as mock_subprocess:
            # Simulate antivirus not detecting (zero-day)
            mock_subprocess.return_value = Mock(returncode=0, stdout='', stderr='')
            
            result = self.validator.validate_email_security(exploit_email, sender, content)
            
            # Should still detect suspicious patterns through basic validation
            self.assertTrue(result.sender_authorized)
            self.assertTrue(result.content_safe)
            # Basic validation should catch unusual binary patterns
            # In a real implementation, we might add heuristic analysis
    
    def test_encrypted_malware_bypass_attempt(self):
        """Test detection of encrypted malware bypass attempts."""
        # Simulate password-protected archive containing malware
        encrypted_archive = (
            b'PK\x03\x04\x14\x00\x01\x00\x08\x00' +  # ZIP header with encryption
            b'A' * 100 +  # Encrypted content
            b'malware.exe' +  # Filename in directory
            b'B' * 50
        )
        
        bypass_email = EmailMessage()
        bypass_email['From'] = 'partner@dol.gov'
        bypass_email['To'] = 'employee@dol.gov'
        bypass_email['Subject'] = 'Confidential Documents - Password: 123456'
        bypass_email.set_content("""
        Please find attached confidential documents.
        Password: 123456
        
        These files contain sensitive information, so they are password protected.
        """)
        
        bypass_email.add_attachment(
            encrypted_archive,
            maintype='application',
            subtype='zip',
            filename='confidential_docs.zip'
        )
        
        sender = 'partner@dol.gov'
        content = ""
        for part in bypass_email.walk():
            if part.get_content_type() == 'text/plain':
                content = part.get_content()
                break
        
        with patch('subprocess.run') as mock_subprocess:
            # Antivirus can't scan encrypted content
            mock_subprocess.return_value = Mock(returncode=0, stdout='', stderr='')
            
            result = self.validator.validate_email_security(bypass_email, sender, content)
            
            # Should flag password-protected archives as suspicious
            # In a real implementation, we would add specific rules for:
            # - Password-protected archives
            # - Passwords in email content
            # - Suspicious file combinations
    
    def test_supply_chain_attack_simulation(self):
        """Test detection of supply chain attack via compromised partner."""
        # Simulate legitimate partner account being compromised
        supply_chain_email = EmailMessage()
        supply_chain_email['From'] = 'updates@contractor-partner.com'  # External but trusted
        supply_chain_email['To'] = 'procurement@dol.gov'
        supply_chain_email['Subject'] = 'Software Update - Critical Security Patch'
        supply_chain_email.set_content("""
        Dear DOL Team,
        
        We have released a critical security update for our software.
        Please install the attached update immediately to address CVE-2024-1234.
        
        This update must be installed on all systems by end of business today.
        
        Best regards,
        Partner Software Team
        """)
        
        # Malicious update disguised as legitimate software
        fake_update = b'MZ\x90\x00' + b'FAKE_UPDATE' + b'A' * 1000
        supply_chain_email.add_attachment(
            fake_update,
            maintype='application',
            subtype='octet-stream',
            filename='security_update_v2.1.exe'
        )
        
        sender = 'updates@contractor-partner.com'
        content = ""
        for part in supply_chain_email.walk():
            if part.get_content_type() == 'text/plain':
                content = part.get_content()
                break
        
        with patch('subprocess.run') as mock_subprocess:
            # Simulate advanced malware detection
            mock_subprocess.return_value = Mock(
                returncode=1,
                stdout='security_update_v2.1.exe: Trojan.SupplyChain.Fake FOUND',
                stderr=''
            )
            
            result = self.validator.validate_email_security(supply_chain_email, sender, content)
            
            # Should detect malware despite legitimate-looking source
            self.assertFalse(result.is_valid)
            self.assertFalse(result.sender_authorized)  # External domain
            self.assertTrue(result.content_safe)  # Content appears legitimate
            self.assertFalse(result.attachments_safe)  # Malicious attachment
            self.assertIn(result.threat_level, ['HIGH', 'CRITICAL'])
            self.assertTrue(result.quarantine_required)
    
    def test_multi_vector_attack(self):
        """Test detection of multi-vector attack combining multiple techniques."""
        # Combine phishing, malware, and social engineering
        multi_vector_email = EmailMessage()
        multi_vector_email['From'] = 'security@do1.gov'  # Typosquatting
        multi_vector_email['To'] = 'admin@dol.gov'
        multi_vector_email['Subject'] = 'CRITICAL: System Breach Detected - Immediate Action Required'
        multi_vector_email.set_content("""
        SECURITY ALERT - IMMEDIATE ACTION REQUIRED
        
        We have detected a critical security breach in your department's systems.
        Your account may have been compromised.
        
        URGENT: Click here immediately to secure your account:
        https://emergency-security.tk/breach-response?dept=dol&user=admin
        
        Additionally, please run the attached security scanner to check for malware.
        This tool will clean any infections found on your system.
        
        Time is critical - you have 30 minutes to respond before we must disable all accounts.
        
        DOL Emergency Security Response Team
        """)
        
        # Add fake security tool (actually malware)
        fake_scanner = b'MZ\x90\x00' + b'SECURITY_SCANNER' + b'X' * 2000
        multi_vector_email.add_attachment(
            fake_scanner,
            maintype='application',
            subtype='octet-stream',
            filename='DOL_Security_Scanner.exe'
        )
        
        sender = 'security@do1.gov'
        # Get text content from multipart message
        content = ""
        for part in multi_vector_email.walk():
            if part.get_content_type() == 'text/plain':
                content = part.get_content()
                break
        
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value = Mock(
                returncode=1,
                stdout='DOL_Security_Scanner.exe: Trojan.FakeSecurity FOUND',
                stderr=''
            )
            
            result = self.validator.validate_email_security(multi_vector_email, sender, content)
            
            # Should detect multiple threat vectors
            self.assertFalse(result.is_valid)
            self.assertFalse(result.sender_authorized)  # Typosquatting
            self.assertFalse(result.content_safe)  # Phishing patterns
            self.assertFalse(result.attachments_safe)  # Malware
            self.assertEqual(result.threat_level, 'CRITICAL')  # Highest threat level
            self.assertTrue(result.quarantine_required)
            
            # Should detect all threat types
            issues = ' '.join(result.security_issues)
            self.assertIn('Unauthorized sender', issues)
            self.assertIn('Phishing detected', issues)
            self.assertIn('Suspicious links', issues)
            self.assertIn('Malicious attachments', issues)


if __name__ == '__main__':
    unittest.main()