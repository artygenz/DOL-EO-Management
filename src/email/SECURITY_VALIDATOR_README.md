# Email Security Validator

## Overview

The Email Security Validator is a government-grade security validation system designed to protect federal email systems from sophisticated threats. It implements comprehensive security controls including sender authorization, attachment scanning, content analysis, and digital signature verification.

## Features

### 🔐 Government-Grade Security Controls

- **Sender Authorization**: Validates email senders against government domain whitelist
- **Attachment Scanning**: Integrates with government-approved antivirus engines
- **Content Safety Analysis**: Detects phishing, malicious patterns, and suspicious links
- **Digital Signature Verification**: Validates email authenticity using cryptographic signatures
- **Threat Level Assessment**: Calculates risk levels (LOW, MEDIUM, HIGH, CRITICAL)
- **Automatic Quarantine**: Isolates suspicious emails for security review

### 🛡️ Threat Detection Capabilities

- **Phishing Detection**: Advanced pattern matching for social engineering attacks
- **Malware Scanning**: Multi-engine antivirus integration with fallback validation
- **Typosquatting Detection**: Identifies domain impersonation attempts
- **Content Analysis**: Detects malicious scripts, suspicious URLs, and dangerous patterns
- **File Type Validation**: Blocks dangerous file extensions and executable signatures
- **Multi-Vector Attacks**: Comprehensive analysis of combined threat techniques

### 📊 Compliance and Audit

- **FISMA Compliance**: Meets federal security baseline requirements
- **FedRAMP Authorization**: Government cloud deployment ready
- **NIST Framework**: Implements cybersecurity framework standards
- **Immutable Audit Logs**: Complete traceability with cryptographic signing
- **Incident Reporting**: Automated security incident generation and alerting

## Quick Start

### Basic Usage

```python
from src.email.security_validator import SecurityValidatorFactory

# Create validator with default government configuration
validator = SecurityValidatorFactory.create_default_validator()

# Validate an email
result = validator.validate_email_security(email_message, sender, content)

if result.is_valid:
    print("Email passed security validation")
else:
    print(f"Security issues detected: {result.security_issues}")
    if result.quarantine_required:
        print("Email has been quarantined for review")
```

### Custom Configuration

```python
config = {
    'government_domains': ['dol.gov', 'labor.gov', 'custom.gov'],
    'antivirus_engine': '/usr/bin/clamav',
    'max_attachment_size': 25 * 1024 * 1024,  # 25MB
    'quarantine_directory': '/secure/quarantine',
    'signature_verification_enabled': True,
    'trusted_ca_certificates': '/etc/ssl/certs'
}

validator = SecurityValidatorFactory.create_validator(config)
```

## Configuration Options

| Parameter | Description | Default |
|-----------|-------------|---------|
| `government_domains` | List of authorized government domains | `['dol.gov', 'labor.gov', 'osha.gov', 'bls.gov']` |
| `antivirus_engine` | Path to antivirus scanning engine | `'/usr/bin/clamav'` |
| `max_attachment_size` | Maximum attachment size in bytes | `50MB` |
| `quarantine_directory` | Directory for quarantined files | `'/tmp/quarantine'` |
| `signature_verification_enabled` | Enable digital signature verification | `True` |
| `trusted_ca_certificates` | Path to trusted CA certificates | `'/etc/ssl/certs'` |

## Security Validation Process

### 1. Sender Authorization
- Extracts domain from sender email address
- Validates against government domain whitelist
- Detects typosquatting and domain impersonation

### 2. Content Safety Analysis
- Scans for phishing patterns and social engineering
- Identifies suspicious URLs and link shorteners
- Detects malicious scripts and code injection attempts
- Calculates confidence score based on threat indicators

### 3. Attachment Security Scanning
- Integrates with ClamAV and other antivirus engines
- Validates file sizes against configured limits
- Performs basic file type and signature validation
- Quarantines malicious attachments automatically

### 4. Digital Signature Verification
- Validates S/MIME and PGP/MIME signatures
- Verifies certificate trust chains
- Ensures message integrity and authenticity

### 5. Threat Level Calculation
- Combines all validation results
- Assigns threat levels: LOW, MEDIUM, HIGH, CRITICAL
- Determines quarantine requirements
- Generates security incident reports

## Threat Detection Examples

### Phishing Email Detection
```python
# Phishing patterns automatically detected:
# - "URGENT ACTION REQUIRED"
# - "Click here immediately"
# - "Verify your account now"
# - Suspicious domains (.tk, .ml, IP addresses)
# - URL shorteners (bit.ly, tinyurl)
```

### Malware Attachment Detection
```python
# Dangerous file types blocked:
# - Executables (.exe, .bat, .cmd, .scr)
# - Scripts (.vbs, .js, .jar)
# - Suspicious extensions (.pdf.exe, .doc.scr)
# - Files with executable signatures (PE, ELF, Java)
```

### Advanced Threat Scenarios
```python
# Multi-vector attacks detected:
# - Typosquatting + phishing + malware
# - Social engineering + credential harvesting
# - Supply chain attacks via compromised partners
# - Zero-day exploits with unusual patterns
```

## Integration with Email Agent

The Security Validator integrates seamlessly with the Email Agent processing pipeline:

```python
from src.email import EmailSecurityValidator, SecurityValidatorFactory

class EmailProcessor:
    def __init__(self):
        self.security_validator = SecurityValidatorFactory.create_default_validator()
    
    def process_email(self, email_message, sender):
        # Extract content
        content = self.extract_content(email_message)
        
        # Validate security
        security_result = self.security_validator.validate_email_security(
            email_message, sender, content
        )
        
        if not security_result.is_valid:
            self.handle_security_threat(security_result)
            return False
        
        # Continue with normal processing
        return self.continue_processing(email_message)
```

## Testing

### Unit Tests
```bash
python -m pytest tests/email/test_security_validator.py -v
```

### Threat Scenario Tests
```bash
python -m pytest tests/email/test_security_threat_scenarios.py -v
```

### Demo Script
```bash
python examples/security_validator_demo.py
```

## Security Considerations

### Antivirus Integration
- Requires ClamAV or compatible antivirus engine
- Supports timeout and error handling for scan failures
- Implements fallback validation when antivirus unavailable
- Regular signature updates recommended

### Quarantine Management
- Quarantined files stored with metadata and timestamps
- Automatic cleanup policies should be implemented
- Access controls required for quarantine directory
- Incident response procedures for quarantined items

### Performance Optimization
- Attachment scanning can be resource-intensive
- Consider implementing scan result caching
- Monitor system resources during high-volume periods
- Scale horizontally for increased throughput

## Compliance and Certification

### Federal Requirements Met
- ✅ FISMA Moderate Baseline
- ✅ FedRAMP Authorization Ready
- ✅ NIST Cybersecurity Framework
- ✅ Privacy Impact Assessment Controls
- ✅ Government Security Standards

### Audit and Reporting
- Complete audit trail for all security decisions
- Immutable log entries with cryptographic signatures
- Automated compliance reporting capabilities
- Integration with SIEM and security monitoring systems

## Troubleshooting

### Common Issues

**Antivirus Not Found**
```
Error: [Errno 2] No such file or directory: 'clamscan'
Solution: Install ClamAV or configure correct antivirus path
```

**Permission Denied on Quarantine**
```
Error: Permission denied: '/tmp/quarantine'
Solution: Ensure write permissions for quarantine directory
```

**High False Positive Rate**
```
Issue: Legitimate emails being quarantined
Solution: Adjust threat detection thresholds or whitelist patterns
```

### Debug Mode
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Enable detailed security validation logging
validator = SecurityValidatorFactory.create_default_validator()
```

## Contributing

When contributing to the Security Validator:

1. **Security First**: All changes must maintain or improve security posture
2. **Test Coverage**: Include comprehensive tests for new threat scenarios
3. **Documentation**: Update this README for new features or configuration options
4. **Compliance**: Ensure changes maintain federal compliance requirements
5. **Performance**: Consider impact on email processing throughput

## Support

For security-related issues or questions:
- Review the comprehensive test suite for usage examples
- Check the demo script for implementation patterns
- Consult federal security guidelines for compliance requirements
- Follow incident response procedures for security threats

---

**⚠️ Security Notice**: This system is designed for federal government use and implements security controls required for sensitive communications. Ensure proper configuration and regular updates for optimal protection.