#!/usr/bin/env python3

"""
Test script for the new email sending functionality.

This script demonstrates how to use the EmailService to send emails
both to outbox and via SMTP.

Environment Variables Required:
- EMAIL_USER: Your email address
- EMAIL_PASS: Your email password
- EMAIL_HOST: SMTP host (default: smtpout.secureserver.net)
- EMAIL_PORT: SMTP port (default: 465)
- SMTP_HOST: SMTP host (default: smtpout.secureserver.net)
- SMTP_PORT: SMTP port (default: 465)
- OUTBOX_DIR: Directory to save emails (default: /tmp/outbox)
"""

import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.email.email_service import EmailService, Attachment

def test_outbox_only():
    """Test saving email to outbox only (existing functionality)"""
    print("=== Testing Outbox Only ===")
    
    email_service = EmailService()
    
    # Create a simple attachment
    attachment = Attachment(
        filename="test.txt",
        content_type="text/plain",
        data=b"This is a test attachment content."
    )
    
    try:
        message_id = email_service.send(
            to=["test@example.com"],
            subject="Test Email - Outbox Only",
            body_text="This is a test email that will be saved to outbox only.",
            body_html="<h1>Test Email</h1><p>This is a test email that will be saved to outbox only.</p>",
            attachments=[attachment],
            email_log_id="test-123",
            email_type="test"
        )
        
        print(f"✅ Email saved to outbox with message_id: {message_id}")
        print(f"📁 Check the outbox directory: {email_service.out_dir}")
        
    except Exception as e:
        print(f"❌ Error saving to outbox: {e}")

def test_smtp_and_outbox():
    """Test sending email via SMTP and saving to outbox"""
    print("\n=== Testing SMTP + Outbox ===")
    
    # Check if required environment variables are set
    required_vars = ["EMAIL_USER", "EMAIL_PASS"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {missing_vars}")
        print("Please set these variables before testing SMTP functionality.")
        return
    
    email_service = EmailService()
    
    # Create a simple attachment
    attachment = Attachment(
        filename="test.txt",
        content_type="text/plain",
        data=b"This is a test attachment content for SMTP."
    )
    
    try:
        message_id = email_service.send_and_save(
            to=["test@example.com"],  # Replace with actual test email
            subject="Test Email - SMTP + Outbox",
            body_text="This is a test email that will be sent via SMTP and saved to outbox.",
            body_html="<h1>Test Email</h1><p>This is a test email that will be sent via SMTP and saved to outbox.</p>",
            attachments=[attachment],
            email_log_id="test-smtp-123",
            email_type="test_smtp"
        )
        
        print(f"✅ Email sent via SMTP and saved to outbox with message_id: {message_id}")
        print(f"📁 Check the outbox directory: {email_service.out_dir}")
        
    except Exception as e:
        print(f"❌ Error sending via SMTP: {e}")
        print("Note: Email may still be saved to outbox even if SMTP fails.")

def test_simple_text_email():
    """Test sending a simple text-only email"""
    print("\n=== Testing Simple Text Email ===")
    
    email_service = EmailService()
    
    try:
        message_id = email_service.send_and_save(
            to=["kevin.brown@lumenlighthouse.ai"],  # Replace with actual test email
            subject="Simple Test Email",
            body_text="This is a simple text-only test email.",
            email_log_id="test-simple-123",
            email_type="test_simple"
        )
        
        print(f"✅ Simple email sent with message_id: {message_id}")
        
    except Exception as e:
        print(f"❌ Error sending simple email: {e}")

def main():
    """Run all email sending tests"""
    print("🧪 Email Service Testing")
    print("=" * 50)
    
    # Test 1: Outbox only (should always work)
    # test_outbox_only()
    
    # Test 2: Simple text email
    test_simple_text_email()
    
    # Test 3: SMTP + Outbox (requires environment variables)
    # test_smtp_and_outbox()
    
    print("\n" + "=" * 50)
    print("🏁 Testing complete!")
    print("\nNotes:")
    print("- Outbox emails are saved to the configured OUTBOX_DIR")
    print("- SMTP emails require proper environment variables")
    print("- Check logs for detailed error information")

if __name__ == "__main__":
    main()
