"""
Email Security Validator Demo

This script demonstrates the government-grade security validation capabilities
of the Email Agent system, including sender authorization, content analysis,
attachment scanning, and digital signature verification.
"""

import logging
import sys
from email.message import EmailMessage
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from src.email.security_validator import SecurityValidatorFactory


def setup_logging():
    """Set up logging for the demo."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def create_legitimate_email():
    """Create a legitimate government email for testing."""
    email = EmailMessage()
    email['From'] = 'director@dol.gov'
    email['To'] = 'staff@dol.gov'
    email['Subject'] = 'Quarterly Safety Report'
    email.set_content("""
    Dear Team,
    
    Please find attached the quarterly workplace safety report.
    Review the findings and prepare implementation recommendations.
    
    Meeting scheduled for next Friday at 2 PM to discuss.
    
    Best regards,
    Safety Director
    """)
    
    # Add safe PDF attachment (simulated)
    pdf_content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj'
    email.add_attachment(
        pdf_content,
        maintype='application',
        subtype='pdf',
        filename='safety_report_Q1.pdf'
    )
    
    return email


def create_phishing_email():
    """Create a phishing email for testing."""
    email = EmailMessage()
    email['From'] = 'security@do1-gov.com'  # Typosquatting
    email['To'] = 'employee@dol.gov'
    email['Subject'] = 'URGENT: Account Verification Required'
    email.set_content("""
    URGENT ACTION REQUIRED!
    
    Your account will be suspended in 24 hours.
    Click here immediately to verify your account now:
    http://fake-verification.tk/urgent
    
    Confirm your identity or lose access permanently.
    """)
    
    return email


def main():
    """Run the security validator demo."""
    setup_logging()
    
    print("=== Email Security Validator Demo ===\n")
    
    # Create security validator with default configuration
    validator = SecurityValidatorFactory.create_default_validator()
    
    print("1. Testing Legitimate Government Email")
    print("-" * 40)
    
    legitimate_email = create_legitimate_email()
    sender = 'director@dol.gov'
    # Get text content from multipart message
    content = ""
    for part in legitimate_email.walk():
        if part.get_content_type() == 'text/plain':
            content = part.get_content()
            break
    
    result = validator.validate_email_security(legitimate_email, sender, content)
    
    print(f"Sender: {sender}")
    print(f"Valid: {result.is_valid}")
    print(f"Sender Authorized: {result.sender_authorized}")
    print(f"Content Safe: {result.content_safe}")
    print(f"Attachments Safe: {result.attachments_safe}")
    print(f"Threat Level: {result.threat_level}")
    print(f"Quarantine Required: {result.quarantine_required}")
    if result.security_issues:
        print(f"Security Issues: {result.security_issues}")
    
    print("\n2. Testing Phishing Email")
    print("-" * 40)
    
    phishing_email = create_phishing_email()
    sender = 'security@do1-gov.com'
    content = phishing_email.get_content()
    
    result = validator.validate_email_security(phishing_email, sender, content)
    
    print(f"Sender: {sender}")
    print(f"Valid: {result.is_valid}")
    print(f"Sender Authorized: {result.sender_authorized}")
    print(f"Content Safe: {result.content_safe}")
    print(f"Attachments Safe: {result.attachments_safe}")
    print(f"Threat Level: {result.threat_level}")
    print(f"Quarantine Required: {result.quarantine_required}")
    if result.security_issues:
        print(f"Security Issues: {result.security_issues}")
    
    print("\n=== Demo Complete ===")


if __name__ == '__main__':
    main()